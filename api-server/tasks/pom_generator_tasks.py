"""
POM Generator Celery Tasks
Generates Page Object Model code using AI
"""

import os
import json
import logging
import redis
from celery import shared_task
from anthropic import Anthropic
from models.database import SessionLocal, CompanyProductSubscription
from services.encryption_service import get_decrypted_api_key
from services.ai_budget_service import get_budget_service, BudgetExceededError

logger = logging.getLogger(__name__)


def _get_redis_client():
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0
    )


def _get_api_key(company_id: int, product_id: int = 1) -> str:
    """Get API key - BYOK if available, otherwise system key"""
    db = SessionLocal()
    try:
        redis_client = _get_redis_client()
        budget_service = get_budget_service(redis_client)

        has_budget, remaining, total = budget_service.check_budget(db, company_id, product_id)
        if not has_budget:
            raise BudgetExceededError(company_id, total, total - remaining)

        subscription = db.query(CompanyProductSubscription).filter(
            CompanyProductSubscription.company_id == company_id,
            CompanyProductSubscription.product_id == product_id
        ).first()

        if subscription and subscription.customer_claude_api_key:
            return get_decrypted_api_key(company_id, subscription.customer_claude_api_key)

        return os.getenv("ANTHROPIC_API_KEY")
    finally:
        db.close()


@shared_task(name='tasks.generate_pom', bind=True)
def generate_pom(
        self,
        form_page_data: dict,
        paths_data: list,
        language: str,
        framework: str,
        style: str = 'basic',
        company_id: int = None,
        product_id: int = 1
):
    """
    Generate POM code using Claude AI
    Returns the generated code as task result
    """
    try:
        # Update state to processing
        self.update_state(state='PROCESSING', meta={'progress': 10, 'message': 'Building prompt...'})

        # Build the prompt
        prompt = build_pom_prompt(form_page_data, paths_data, language, framework, style)

        # Update progress
        self.update_state(state='PROCESSING', meta={'progress': 30, 'message': 'Calling AI...'})

        # Get API key (BYOK or system)
        if company_id:
            api_key = _get_api_key(company_id, product_id)
        else:
            api_key = os.getenv("ANTHROPIC_API_KEY")

        client = Anthropic(api_key=api_key)

        response = client.messages.create(
            #model="claude-sonnet-4-20250514",
            model = "claude-sonnet-4-5-20250929",
            max_tokens=8000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        generated_code = response.content[0].text

        # Extract code from response (remove markdown if present)
        if "```" in generated_code:
            lines = generated_code.split("\n")
            code_lines = []
            in_code_block = False
            for line in lines:
                if line.startswith("```") and not in_code_block:
                    in_code_block = True
                    continue
                elif line.startswith("```") and in_code_block:
                    in_code_block = False
                    continue
                elif in_code_block:
                    code_lines.append(line)
            generated_code = "\n".join(code_lines)

        logger.info(f"POM generation completed for task {self.request.id}")

        # Return the result (Celery stores it automatically)
        return {
            'success': True,
            'code': generated_code,
            'language': language,
            'framework': framework
        }

    except Exception as e:
        logger.error(f"POM generation failed: {str(e)}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise


def build_pom_prompt(form_page_data: dict, paths_data: list, language: str, framework: str, style: str = 'basic') -> str:
    """Build the prompt for POM generation"""

    navigation_steps = form_page_data.get('navigation_steps', [])
    has_navigation = navigation_steps and len(navigation_steps) > 0

    # Framework-specific instructions
    framework_instructions = ""
    if framework == "cypress":
        framework_instructions = """
**Cypress-Specific Requirements:**
- Use Cypress command syntax (cy.get(), cy.click(), cy.type(), etc.)
- Use cy.visit() for navigation
- Selectors should use cy.get() with CSS selectors
- For assertions use cy.should() or expect()
- Export the page object as a class or object
- Use cy.wrap() for chaining when needed
- Do NOT use async/await - Cypress commands are automatically queued
"""
    elif framework == "playwright":
        framework_instructions = """
**Playwright-Specific Requirements:**
- Use Playwright's page.locator() for element selection
- Use async/await syntax for all operations
- Use page.goto() for navigation
- Use locator.click(), locator.fill(), locator.selectOption()
- For assertions use expect(locator).toHaveText(), expect(locator).toBeVisible() etc.
"""
    elif framework == "selenium":
        framework_instructions = """
**Selenium-Specific Requirements:**
- Use WebDriver find_element methods
- Use By class for locators (By.ID, By.CSS_SELECTOR, By.XPATH)
- Use explicit waits with WebDriverWait and expected_conditions
- Use Select class for dropdowns
"""

    # Style-specific instructions for Java
    style_instructions = ""
    if language == "java" and style == "pagefactory":
        style_instructions = """
**Page Factory Style Requirements:**
- Use @FindBy annotations for ALL element locators
- Initialize elements with PageFactory.initElements(driver, this) in constructor
- Import org.openqa.selenium.support.FindBy
- Import org.openqa.selenium.support.PageFactory
- Import org.openqa.selenium.support.How (optional, for How.ID etc.)
- Locators should be WebElement fields annotated with @FindBy
- Example format:
  @FindBy(id = "username")
  private WebElement usernameInput;
  
  @FindBy(css = ".submit-btn")
  private WebElement submitButton;
"""

    prompt = f"""Generate a complete Page Object Model (POM) class for the following form page.

**Language:** {language}
**Framework:** {framework}
{f'**Style:** Page Factory' if style == 'pagefactory' else ''}
{framework_instructions}
{style_instructions}

**Form Page Information:**
- Class Name: {form_page_data.get('form_name', 'FormPage').replace(' ', '')}Page
- URL: {form_page_data.get('url', '')}

**Navigation Steps to Reach the Form:**
{json.dumps(navigation_steps, indent=2) if has_navigation else "Direct URL navigation only"}

**Paths (Form Interaction Steps):**
{json.dumps(paths_data, indent=2)}

**Requirements:**
1. Create a complete, production-ready POM class
2. Include a `navigate()` method that:
   - Navigates to the URL: {form_page_data.get('url', '')}
   - If navigation steps exist, execute them after URL navigation
3. Include all locators from both navigation steps and path steps
4. Create a method for each path (e.g., `complete_path_1()`, `complete_path_2()`)
5. Each path method should:
   - Call `navigate()` first (or assume already navigated)
   - Execute all steps in the path in order
6. Use proper {language} conventions and {framework} best practices
7. Include docstrings/comments explaining each method
8. Handle different action types appropriately:
   - "fill" -> send_keys / fill / type (input text)
   - "click" -> click element
   - "select" -> select dropdown option by visible text
   - "verify" -> create assertion method (assert element contains expected value)
   - "hover" -> hover/mouse over element
   - "wait" -> explicit wait for element
   - "check" / "uncheck" -> checkbox interactions
9. For verify steps, create meaningful assertions
10. Include proper imports at the top
11. Make locators as class constants/properties
12. Include a constructor method that accepts the driver/page instance

Generate ONLY the code, no explanations before or after. The code should be ready to copy and use.
"""

    return prompt