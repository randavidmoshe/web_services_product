--
-- PostgreSQL database dump
--

\restrict lJUb1q1B1u9xAaOidihfh6avDhDXPafaKOZtu2z6kNI2nvKkpjmj01PYBB4b1cC

-- Dumped from database version 15.14
-- Dumped by pg_dump version 17.6 (Debian 17.6-0+deb13u1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agent_instances; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_instances (
    id integer NOT NULL,
    user_id integer NOT NULL,
    machine_id character varying(255),
    platform character varying(50),
    agent_version character varying(50),
    status character varying(50) DEFAULT 'offline'::character varying,
    last_heartbeat timestamp without time zone,
    connected_at timestamp without time zone DEFAULT now(),
    disconnected_at timestamp without time zone
);


ALTER TABLE public.agent_instances OWNER TO postgres;

--
-- Name: agent_instances_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.agent_instances_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.agent_instances_id_seq OWNER TO postgres;

--
-- Name: agent_instances_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.agent_instances_id_seq OWNED BY public.agent_instances.id;


--
-- Name: agent_tasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_tasks (
    id integer NOT NULL,
    task_id character varying(100) NOT NULL,
    company_id integer NOT NULL,
    user_id integer NOT NULL,
    agent_id character varying(100),
    task_type character varying(50) NOT NULL,
    parameters jsonb NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    result jsonb,
    error_message text,
    created_at timestamp without time zone DEFAULT now(),
    started_at timestamp without time zone,
    completed_at timestamp without time zone
);


ALTER TABLE public.agent_tasks OWNER TO postgres;

--
-- Name: TABLE agent_tasks; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.agent_tasks IS 'Tasks queued for agents to execute';


--
-- Name: agent_tasks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.agent_tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.agent_tasks_id_seq OWNER TO postgres;

--
-- Name: agent_tasks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.agent_tasks_id_seq OWNED BY public.agent_tasks.id;


--
-- Name: agents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agents (
    id integer NOT NULL,
    agent_id character varying(100) NOT NULL,
    company_id integer NOT NULL,
    user_id integer NOT NULL,
    hostname character varying(255),
    platform character varying(50),
    version character varying(20),
    status character varying(20) DEFAULT 'offline'::character varying,
    last_heartbeat timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.agents OWNER TO postgres;

--
-- Name: TABLE agents; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.agents IS 'Agents running on customer networks';


--
-- Name: agents_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.agents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.agents_id_seq OWNER TO postgres;

--
-- Name: agents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.agents_id_seq OWNED BY public.agents.id;


--
-- Name: api_usage; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.api_usage (
    id integer NOT NULL,
    company_id integer NOT NULL,
    product_id integer NOT NULL,
    subscription_id integer NOT NULL,
    user_id integer,
    crawl_session_id integer,
    operation_type character varying(100),
    tokens_used integer NOT NULL,
    api_cost numeric(10,4) NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.api_usage OWNER TO postgres;

--
-- Name: api_usage_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.api_usage_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.api_usage_id_seq OWNER TO postgres;

--
-- Name: api_usage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.api_usage_id_seq OWNED BY public.api_usage.id;


--
-- Name: automation_users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.automation_users (
    id integer NOT NULL,
    network_id integer NOT NULL,
    username character varying(255) NOT NULL,
    password_encrypted character varying(500) NOT NULL,
    description character varying(500),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.automation_users OWNER TO postgres;

--
-- Name: automation_users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.automation_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.automation_users_id_seq OWNER TO postgres;

--
-- Name: automation_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.automation_users_id_seq OWNED BY public.automation_users.id;


--
-- Name: companies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.companies (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    billing_email character varying(255),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.companies OWNER TO postgres;

--
-- Name: companies_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.companies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.companies_id_seq OWNER TO postgres;

--
-- Name: companies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.companies_id_seq OWNED BY public.companies.id;


--
-- Name: company_product_subscriptions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.company_product_subscriptions (
    id integer NOT NULL,
    company_id integer NOT NULL,
    product_id integer NOT NULL,
    status character varying(50) DEFAULT 'trial'::character varying,
    is_trial boolean DEFAULT true,
    trial_ends_at timestamp without time zone,
    monthly_subscription_cost numeric(10,2) DEFAULT 1000.00 NOT NULL,
    monthly_claude_budget numeric(10,2) DEFAULT 500.00 NOT NULL,
    claude_used_this_month numeric(10,2) DEFAULT 0.00,
    budget_reset_date date DEFAULT (CURRENT_DATE + '1 mon'::interval),
    customer_claude_api_key character varying(500),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.company_product_subscriptions OWNER TO postgres;

--
-- Name: company_product_subscriptions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.company_product_subscriptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.company_product_subscriptions_id_seq OWNER TO postgres;

--
-- Name: company_product_subscriptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.company_product_subscriptions_id_seq OWNED BY public.company_product_subscriptions.id;


--
-- Name: crawl_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crawl_sessions (
    id integer NOT NULL,
    company_id integer NOT NULL,
    product_id integer NOT NULL,
    project_id integer,
    network_id integer,
    user_id integer NOT NULL,
    agent_instance_id integer,
    session_type character varying(50) NOT NULL,
    status character varying(50) DEFAULT 'pending'::character varying,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    pages_crawled integer DEFAULT 0,
    forms_found integer DEFAULT 0,
    error_message text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.crawl_sessions OWNER TO postgres;

--
-- Name: crawl_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.crawl_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.crawl_sessions_id_seq OWNER TO postgres;

--
-- Name: crawl_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.crawl_sessions_id_seq OWNED BY public.crawl_sessions.id;


--
-- Name: form_details; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.form_details (
    id integer NOT NULL,
    company_id integer NOT NULL,
    product_id integer NOT NULL,
    form_page_id integer NOT NULL,
    form_name character varying(255),
    form_action character varying(500),
    form_method character varying(10),
    fields jsonb,
    validation_rules jsonb,
    ai_analysis jsonb,
    discovered_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.form_details OWNER TO postgres;

--
-- Name: form_details_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.form_details_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.form_details_id_seq OWNER TO postgres;

--
-- Name: form_details_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.form_details_id_seq OWNED BY public.form_details.id;


--
-- Name: form_pages_discovered; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.form_pages_discovered (
    id integer NOT NULL,
    company_id integer NOT NULL,
    product_id integer NOT NULL,
    crawl_session_id integer NOT NULL,
    url character varying(1000) NOT NULL,
    page_title character varying(500),
    forms_count integer DEFAULT 0,
    screenshot_url character varying(1000),
    discovered_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.form_pages_discovered OWNER TO postgres;

--
-- Name: form_pages_discovered_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.form_pages_discovered_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.form_pages_discovered_id_seq OWNER TO postgres;

--
-- Name: form_pages_discovered_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.form_pages_discovered_id_seq OWNED BY public.form_pages_discovered.id;


--
-- Name: migrations_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.migrations_history (
    id integer NOT NULL,
    migration_id integer NOT NULL,
    filename character varying(255) NOT NULL,
    executed_at timestamp without time zone DEFAULT now(),
    rolled_back_at timestamp without time zone,
    status character varying(20) DEFAULT 'applied'::character varying
);


ALTER TABLE public.migrations_history OWNER TO postgres;

--
-- Name: migrations_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.migrations_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.migrations_history_id_seq OWNER TO postgres;

--
-- Name: migrations_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.migrations_history_id_seq OWNED BY public.migrations_history.id;


--
-- Name: networks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.networks (
    id integer NOT NULL,
    project_id integer NOT NULL,
    company_id integer NOT NULL,
    product_id integer NOT NULL,
    name character varying(255) NOT NULL,
    url character varying(1000) NOT NULL,
    created_by_user_id integer,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.networks OWNER TO postgres;

--
-- Name: networks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.networks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.networks_id_seq OWNER TO postgres;

--
-- Name: networks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.networks_id_seq OWNED BY public.networks.id;


--
-- Name: products; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.products (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    type character varying(50) NOT NULL,
    description text,
    base_price numeric(10,2) DEFAULT 1000.00,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.products OWNER TO postgres;

--
-- Name: products_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.products_id_seq OWNER TO postgres;

--
-- Name: products_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.products_id_seq OWNED BY public.products.id;


--
-- Name: projects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.projects (
    id integer NOT NULL,
    company_id integer NOT NULL,
    product_id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    created_by_user_id integer,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.projects OWNER TO postgres;

--
-- Name: projects_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.projects_id_seq OWNER TO postgres;

--
-- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.projects_id_seq OWNED BY public.projects.id;


--
-- Name: screenshots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.screenshots (
    id integer NOT NULL,
    company_id integer NOT NULL,
    product_id integer,
    crawl_session_id integer,
    form_page_id integer,
    filename character varying(255) NOT NULL,
    image_type character varying(50) NOT NULL,
    description text,
    s3_bucket character varying(255) NOT NULL,
    s3_key character varying(500) NOT NULL,
    s3_url text NOT NULL,
    file_size_bytes integer,
    content_type character varying(100) DEFAULT 'image/png'::character varying,
    width_px integer,
    height_px integer,
    captured_at timestamp without time zone DEFAULT now(),
    uploaded_by_user_id integer,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.screenshots OWNER TO postgres;

--
-- Name: screenshots_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.screenshots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.screenshots_id_seq OWNER TO postgres;

--
-- Name: screenshots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.screenshots_id_seq OWNED BY public.screenshots.id;


--
-- Name: super_admins; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.super_admins (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    name character varying(255),
    created_at timestamp without time zone DEFAULT now(),
    last_login_at timestamp without time zone
);


ALTER TABLE public.super_admins OWNER TO postgres;

--
-- Name: super_admins_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.super_admins_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.super_admins_id_seq OWNER TO postgres;

--
-- Name: super_admins_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.super_admins_id_seq OWNED BY public.super_admins.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    company_id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    name character varying(255),
    role character varying(50) DEFAULT 'user'::character varying,
    agent_api_token character varying(500),
    agent_downloaded_at timestamp without time zone,
    agent_last_active timestamp without time zone,
    created_by_admin_id integer,
    created_at timestamp without time zone DEFAULT now(),
    last_login_at timestamp without time zone
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: agent_instances id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_instances ALTER COLUMN id SET DEFAULT nextval('public.agent_instances_id_seq'::regclass);


--
-- Name: agent_tasks id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_tasks ALTER COLUMN id SET DEFAULT nextval('public.agent_tasks_id_seq'::regclass);


--
-- Name: agents id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agents ALTER COLUMN id SET DEFAULT nextval('public.agents_id_seq'::regclass);


--
-- Name: api_usage id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_usage ALTER COLUMN id SET DEFAULT nextval('public.api_usage_id_seq'::regclass);


--
-- Name: automation_users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.automation_users ALTER COLUMN id SET DEFAULT nextval('public.automation_users_id_seq'::regclass);


--
-- Name: companies id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.companies ALTER COLUMN id SET DEFAULT nextval('public.companies_id_seq'::regclass);


--
-- Name: company_product_subscriptions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_product_subscriptions ALTER COLUMN id SET DEFAULT nextval('public.company_product_subscriptions_id_seq'::regclass);


--
-- Name: crawl_sessions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawl_sessions ALTER COLUMN id SET DEFAULT nextval('public.crawl_sessions_id_seq'::regclass);


--
-- Name: form_details id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.form_details ALTER COLUMN id SET DEFAULT nextval('public.form_details_id_seq'::regclass);


--
-- Name: form_pages_discovered id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.form_pages_discovered ALTER COLUMN id SET DEFAULT nextval('public.form_pages_discovered_id_seq'::regclass);


--
-- Name: migrations_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.migrations_history ALTER COLUMN id SET DEFAULT nextval('public.migrations_history_id_seq'::regclass);


--
-- Name: networks id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.networks ALTER COLUMN id SET DEFAULT nextval('public.networks_id_seq'::regclass);


--
-- Name: products id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products ALTER COLUMN id SET DEFAULT nextval('public.products_id_seq'::regclass);


--
-- Name: projects id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects ALTER COLUMN id SET DEFAULT nextval('public.projects_id_seq'::regclass);


--
-- Name: screenshots id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.screenshots ALTER COLUMN id SET DEFAULT nextval('public.screenshots_id_seq'::regclass);


--
-- Name: super_admins id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.super_admins ALTER COLUMN id SET DEFAULT nextval('public.super_admins_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: agent_instances; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.agent_instances (id, user_id, machine_id, platform, agent_version, status, last_heartbeat, connected_at, disconnected_at) FROM stdin;
\.


--
-- Data for Name: agent_tasks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.agent_tasks (id, task_id, company_id, user_id, agent_id, task_type, parameters, status, result, error_message, created_at, started_at, completed_at) FROM stdin;
1	fde2d9a4-9928-4954-878e-67feb56a9882	1	1	\N	navigate_url	{"url": "https://example.com", "browser": "chrome", "headless": false}	pending	\N	\N	2025-11-16 18:48:02.893808	\N	\N
2	38afe616-4bf7-42cd-8f54-03c56e167d40	1	1	\N	navigate_url	{"url": "https://example.com", "browser": "chrome", "headless": false}	pending	\N	\N	2025-11-16 18:56:16.9617	\N	\N
3	9f5517d7-010a-4b81-8088-8cd63af0bd21	1	1	\N	navigate_url	{"url": "https://example.com", "browser": "chrome", "headless": false}	pending	\N	\N	2025-11-16 19:02:01.848637	\N	\N
4	c1811eaa-ec40-4d76-804b-56545faee726	1	1	\N	navigate_url	{"url": "https://example.com", "browser": "chrome", "headless": false}	pending	\N	\N	2025-11-16 19:03:10.385919	\N	\N
5	0438103e-4371-4736-a002-08219aa2558b	1	1	\N	navigate_url	{"url": "https://example.com", "browser": "chrome", "headless": false}	pending	\N	\N	2025-11-16 19:05:31.80671	\N	\N
6	b123a536-e0f8-438b-a965-6151296baec9	1	1	\N	navigate_url	{"url": "https://example.com", "browser": "chrome", "headless": false}	pending	\N	\N	2025-11-16 19:11:28.358066	\N	\N
7	c26dd4a6-298a-43e1-bcd7-cee7dc546a85	1	1	\N	navigate_url	{"url": "https://example.com", "browser": "chrome", "headless": false}	pending	\N	\N	2025-11-16 19:16:33.37705	\N	\N
8	626e38b1-05de-4227-8987-ff64e41254a5	1	1	\N	navigate_url	{"url": "https://google.com", "browser": "chrome", "headless": false}	pending	\N	\N	2025-11-16 19:19:41.476208	\N	\N
9	b6c54c60-f4c1-47ee-8360-5948015cc099	1	1	agent-test-001	navigate_url	{"url": "https://google.com"}	failed	\N	URL required	2025-11-16 19:25:47.589576	2025-11-16 19:25:48.765318	2025-11-16 19:25:48.780146
10	eea747a7-57c4-45f9-9760-c8f3905d6939	1	1	agent-test-001	navigate_url	{"url": "https://google.com"}	failed	\N	URL required	2025-11-16 19:31:33.292044	2025-11-16 19:31:34.819877	2025-11-16 19:31:34.839824
11	404ee4fb-9535-4bee-9f4a-d065b2b0830a	1	1	agent-test-001	navigate_url	{"url": "https://example.com"}	failed	\N	URL required	2025-11-16 19:32:33.70032	2025-11-16 19:32:35.033394	2025-11-16 19:32:35.059961
12	49ecf051-cd52-4d45-9bc6-79a2eba12b48	1	1	agent-test-001	navigate_url	{"url": "https://example.com"}	failed	\N	URL required	2025-11-16 19:36:11.846759	2025-11-16 19:36:13.529868	2025-11-16 19:36:13.558446
13	74a6b4f0-3b58-4c74-a13f-d3a24a4856ff	1	1	agent-test-001	navigate_url	{"url": "https://google.com"}	failed	\N	AgentSelenium.initialize_browser() got an unexpected keyword argument 'browser'	2025-11-16 20:11:52.325547	2025-11-16 20:11:53.620381	2025-11-16 20:11:53.65598
14	a327a6b5-9172-4dd7-9488-3ebbd185e708	1	1	agent-test-001	navigate_url	{"url": "https://google.com"}	completed	{"url": "https://www.google.com/", "title": "Google", "success": true}	\N	2025-11-16 20:17:02.539862	2025-11-16 20:17:04.02671	2025-11-16 20:17:07.699358
15	0a05b77d-4f78-4549-a53c-0a7674977ed2	1	1	agent-test-001	navigate_url	{"url": "https://google.com"}	assigned	\N	\N	2025-11-17 19:23:48.582722	2025-11-17 19:23:49.466483	\N
16	1de9cdd1-1b08-4f9d-9a25-879c3441eb31	1	1	agent-test-001	navigate_url	{"url": "https://google.com"}	assigned	\N	\N	2025-11-17 19:29:11.770607	2025-11-17 19:29:12.425463	\N
17	eb32ab6f-8d14-4cf2-856f-8e17d623522b	1	1	agent-test-001	navigate_url	{"url": "https://google.com"}	assigned	\N	\N	2025-11-17 19:39:24.753214	2025-11-17 19:43:15.917688	\N
\.


--
-- Data for Name: agents; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.agents (id, agent_id, company_id, user_id, hostname, platform, version, status, last_heartbeat, created_at, updated_at) FROM stdin;
1	agent-test-001	1	1	unknown	linux	2.0.0	idle	2025-11-26 20:53:15.418669	2025-11-16 17:54:01.91949	2025-11-26 20:53:15.418811
\.


--
-- Data for Name: api_usage; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.api_usage (id, company_id, product_id, subscription_id, user_id, crawl_session_id, operation_type, tokens_used, api_cost, created_at) FROM stdin;
\.


--
-- Data for Name: automation_users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.automation_users (id, network_id, username, password_encrypted, description, created_at) FROM stdin;
\.


--
-- Data for Name: companies; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.companies (id, name, billing_email, created_at, updated_at) FROM stdin;
1	Acme Corporation	billing@acme.com	2025-11-16 12:38:23.000853	2025-11-16 12:38:23.000853
\.


--
-- Data for Name: company_product_subscriptions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.company_product_subscriptions (id, company_id, product_id, status, is_trial, trial_ends_at, monthly_subscription_cost, monthly_claude_budget, claude_used_this_month, budget_reset_date, customer_claude_api_key, created_at, updated_at) FROM stdin;
1	1	1	active	f	\N	1000.00	500.00	0.00	2025-12-16	\N	2025-11-16 12:38:23.00197	2025-11-16 12:38:23.00197
\.


--
-- Data for Name: crawl_sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.crawl_sessions (id, company_id, product_id, project_id, network_id, user_id, agent_instance_id, session_type, status, started_at, completed_at, pages_crawled, forms_found, error_message, created_at) FROM stdin;
\.


--
-- Data for Name: form_details; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.form_details (id, company_id, product_id, form_page_id, form_name, form_action, form_method, fields, validation_rules, ai_analysis, discovered_at) FROM stdin;
\.


--
-- Data for Name: form_pages_discovered; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.form_pages_discovered (id, company_id, product_id, crawl_session_id, url, page_title, forms_count, screenshot_url, discovered_at) FROM stdin;
\.


--
-- Data for Name: migrations_history; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.migrations_history (id, migration_id, filename, executed_at, rolled_back_at, status) FROM stdin;
1	4	004_agent_tables_UP.sql	2025-11-16 17:10:26.990844	\N	applied
\.


--
-- Data for Name: networks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.networks (id, project_id, company_id, product_id, name, url, created_by_user_id, created_at) FROM stdin;
1	1	1	1	Production Site	https://shop.acme.com	2	2025-11-16 12:38:23.008336
\.


--
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.products (id, name, type, description, base_price, created_at) FROM stdin;
1	Form Page Testing	form_testing	Discover and analyze form pages	1000.00	2025-11-16 12:38:22.809702
2	Shopping Site Testing	shopping_testing	E-commerce flow testing	1500.00	2025-11-16 12:38:22.809702
3	Marketing Website Testing	marketing_testing	Marketing page analysis	800.00	2025-11-16 12:38:22.809702
4	Advancing Websites by AI	ai_advancement	AI-powered website optimization	2000.00	2025-11-16 12:38:22.809702
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.projects (id, company_id, product_id, name, description, created_by_user_id, created_at, updated_at) FROM stdin;
1	1	1	E-commerce Testing	Test our online store forms	2	2025-11-16 12:38:23.006635	2025-11-16 12:38:23.006635
\.


--
-- Data for Name: screenshots; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.screenshots (id, company_id, product_id, crawl_session_id, form_page_id, filename, image_type, description, s3_bucket, s3_key, s3_url, file_size_bytes, content_type, width_px, height_px, captured_at, uploaded_by_user_id, created_at) FROM stdin;
\.


--
-- Data for Name: super_admins; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.super_admins (id, email, password_hash, name, created_at, last_login_at) FROM stdin;
1	admin@formfinder.com	$2b$12$p7hbvVi9UJVAxdXQsai0e.xya7GZx0lKsACDn.rC3P7PXB0hwte5i	Super Admin	2025-11-16 12:38:22.824499	\N
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, company_id, email, password_hash, name, role, agent_api_token, agent_downloaded_at, agent_last_active, created_by_admin_id, created_at, last_login_at) FROM stdin;
2	1	user@acme.com	$2b$12$p7hbvVi9UJVAxdXQsai0e.xya7GZx0lKsACDn.rC3P7PXB0hwte5i	Jane User	user	\N	\N	\N	2	2025-11-16 12:38:23.005569	\N
1	1	admin@acme.com	$2b$12$p7hbvVi9UJVAxdXQsai0e.xya7GZx0lKsACDn.rC3P7PXB0hwte5i	John Admin	admin	\N	\N	\N	\N	2025-11-16 12:38:23.003929	2025-11-17 08:34:33.782901
\.


--
-- Name: agent_instances_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.agent_instances_id_seq', 1, false);


--
-- Name: agent_tasks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.agent_tasks_id_seq', 17, true);


--
-- Name: agents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.agents_id_seq', 1, true);


--
-- Name: api_usage_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.api_usage_id_seq', 1, false);


--
-- Name: automation_users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.automation_users_id_seq', 1, false);


--
-- Name: companies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.companies_id_seq', 1, true);


--
-- Name: company_product_subscriptions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.company_product_subscriptions_id_seq', 1, true);


--
-- Name: crawl_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.crawl_sessions_id_seq', 1, false);


--
-- Name: form_details_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.form_details_id_seq', 1, false);


--
-- Name: form_pages_discovered_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.form_pages_discovered_id_seq', 1, false);


--
-- Name: migrations_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.migrations_history_id_seq', 1, true);


--
-- Name: networks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.networks_id_seq', 1, true);


--
-- Name: products_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.products_id_seq', 4, true);


--
-- Name: projects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.projects_id_seq', 1, true);


--
-- Name: screenshots_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.screenshots_id_seq', 1, false);


--
-- Name: super_admins_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.super_admins_id_seq', 1, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 2, true);


--
-- Name: agent_instances agent_instances_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_instances
    ADD CONSTRAINT agent_instances_pkey PRIMARY KEY (id);


--
-- Name: agent_tasks agent_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_tasks
    ADD CONSTRAINT agent_tasks_pkey PRIMARY KEY (id);


--
-- Name: agent_tasks agent_tasks_task_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_tasks
    ADD CONSTRAINT agent_tasks_task_id_key UNIQUE (task_id);


--
-- Name: agents agents_agent_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_agent_id_key UNIQUE (agent_id);


--
-- Name: agents agents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_pkey PRIMARY KEY (id);


--
-- Name: api_usage api_usage_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_usage
    ADD CONSTRAINT api_usage_pkey PRIMARY KEY (id);


--
-- Name: automation_users automation_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.automation_users
    ADD CONSTRAINT automation_users_pkey PRIMARY KEY (id);


--
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (id);


--
-- Name: company_product_subscriptions company_product_subscriptions_company_id_product_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_product_subscriptions
    ADD CONSTRAINT company_product_subscriptions_company_id_product_id_key UNIQUE (company_id, product_id);


--
-- Name: company_product_subscriptions company_product_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_product_subscriptions
    ADD CONSTRAINT company_product_subscriptions_pkey PRIMARY KEY (id);


--
-- Name: crawl_sessions crawl_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawl_sessions
    ADD CONSTRAINT crawl_sessions_pkey PRIMARY KEY (id);


--
-- Name: form_details form_details_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.form_details
    ADD CONSTRAINT form_details_pkey PRIMARY KEY (id);


--
-- Name: form_pages_discovered form_pages_discovered_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.form_pages_discovered
    ADD CONSTRAINT form_pages_discovered_pkey PRIMARY KEY (id);


--
-- Name: migrations_history migrations_history_migration_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.migrations_history
    ADD CONSTRAINT migrations_history_migration_id_key UNIQUE (migration_id);


--
-- Name: migrations_history migrations_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.migrations_history
    ADD CONSTRAINT migrations_history_pkey PRIMARY KEY (id);


--
-- Name: networks networks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.networks
    ADD CONSTRAINT networks_pkey PRIMARY KEY (id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: products products_type_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_type_key UNIQUE (type);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: screenshots screenshots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.screenshots
    ADD CONSTRAINT screenshots_pkey PRIMARY KEY (id);


--
-- Name: super_admins super_admins_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.super_admins
    ADD CONSTRAINT super_admins_email_key UNIQUE (email);


--
-- Name: super_admins super_admins_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.super_admins
    ADD CONSTRAINT super_admins_pkey PRIMARY KEY (id);


--
-- Name: users users_agent_api_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_agent_api_token_key UNIQUE (agent_api_token);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_agent_tasks_agent_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agent_tasks_agent_id ON public.agent_tasks USING btree (agent_id);


--
-- Name: idx_agent_tasks_company_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agent_tasks_company_id ON public.agent_tasks USING btree (company_id);


--
-- Name: idx_agent_tasks_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agent_tasks_created_at ON public.agent_tasks USING btree (created_at);


--
-- Name: idx_agent_tasks_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agent_tasks_status ON public.agent_tasks USING btree (status);


--
-- Name: idx_agent_tasks_task_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agent_tasks_task_id ON public.agent_tasks USING btree (task_id);


--
-- Name: idx_agent_tasks_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agent_tasks_user_id ON public.agent_tasks USING btree (user_id);


--
-- Name: idx_agents_agent_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agents_agent_id ON public.agents USING btree (agent_id);


--
-- Name: idx_agents_company_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agents_company_id ON public.agents USING btree (company_id);


--
-- Name: idx_agents_last_heartbeat; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agents_last_heartbeat ON public.agents USING btree (last_heartbeat);


--
-- Name: idx_agents_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agents_status ON public.agents USING btree (status);


--
-- Name: idx_api_usage_company_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_api_usage_company_date ON public.api_usage USING btree (company_id, created_at);


--
-- Name: idx_api_usage_subscription; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_api_usage_subscription ON public.api_usage USING btree (subscription_id, created_at);


--
-- Name: idx_crawl_sessions_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_crawl_sessions_status ON public.crawl_sessions USING btree (status);


--
-- Name: idx_crawl_sessions_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_crawl_sessions_user ON public.crawl_sessions USING btree (user_id);


--
-- Name: idx_form_pages_session; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_form_pages_session ON public.form_pages_discovered USING btree (crawl_session_id);


--
-- Name: idx_projects_company_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_projects_company_product ON public.projects USING btree (company_id, product_id);


--
-- Name: idx_screenshots_company; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_screenshots_company ON public.screenshots USING btree (company_id);


--
-- Name: idx_screenshots_form_page; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_screenshots_form_page ON public.screenshots USING btree (form_page_id);


--
-- Name: idx_screenshots_session; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_screenshots_session ON public.screenshots USING btree (crawl_session_id);


--
-- Name: idx_screenshots_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_screenshots_type ON public.screenshots USING btree (image_type);


--
-- Name: idx_users_company; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_company ON public.users USING btree (company_id);


--
-- Name: agent_instances agent_instances_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_instances
    ADD CONSTRAINT agent_instances_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: agent_tasks agent_tasks_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_tasks
    ADD CONSTRAINT agent_tasks_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(agent_id) ON DELETE SET NULL;


--
-- Name: agent_tasks agent_tasks_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_tasks
    ADD CONSTRAINT agent_tasks_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: agent_tasks agent_tasks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_tasks
    ADD CONSTRAINT agent_tasks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: agents agents_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: agents agents_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: api_usage api_usage_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_usage
    ADD CONSTRAINT api_usage_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: api_usage api_usage_crawl_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_usage
    ADD CONSTRAINT api_usage_crawl_session_id_fkey FOREIGN KEY (crawl_session_id) REFERENCES public.crawl_sessions(id);


--
-- Name: api_usage api_usage_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_usage
    ADD CONSTRAINT api_usage_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: api_usage api_usage_subscription_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_usage
    ADD CONSTRAINT api_usage_subscription_id_fkey FOREIGN KEY (subscription_id) REFERENCES public.company_product_subscriptions(id);


--
-- Name: api_usage api_usage_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_usage
    ADD CONSTRAINT api_usage_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: automation_users automation_users_network_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.automation_users
    ADD CONSTRAINT automation_users_network_id_fkey FOREIGN KEY (network_id) REFERENCES public.networks(id) ON DELETE CASCADE;


--
-- Name: company_product_subscriptions company_product_subscriptions_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_product_subscriptions
    ADD CONSTRAINT company_product_subscriptions_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: company_product_subscriptions company_product_subscriptions_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_product_subscriptions
    ADD CONSTRAINT company_product_subscriptions_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: crawl_sessions crawl_sessions_agent_instance_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawl_sessions
    ADD CONSTRAINT crawl_sessions_agent_instance_id_fkey FOREIGN KEY (agent_instance_id) REFERENCES public.agent_instances(id);


--
-- Name: crawl_sessions crawl_sessions_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawl_sessions
    ADD CONSTRAINT crawl_sessions_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: crawl_sessions crawl_sessions_network_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawl_sessions
    ADD CONSTRAINT crawl_sessions_network_id_fkey FOREIGN KEY (network_id) REFERENCES public.networks(id);


--
-- Name: crawl_sessions crawl_sessions_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawl_sessions
    ADD CONSTRAINT crawl_sessions_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: crawl_sessions crawl_sessions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawl_sessions
    ADD CONSTRAINT crawl_sessions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: crawl_sessions crawl_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawl_sessions
    ADD CONSTRAINT crawl_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: form_details form_details_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.form_details
    ADD CONSTRAINT form_details_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: form_details form_details_form_page_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.form_details
    ADD CONSTRAINT form_details_form_page_id_fkey FOREIGN KEY (form_page_id) REFERENCES public.form_pages_discovered(id) ON DELETE CASCADE;


--
-- Name: form_details form_details_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.form_details
    ADD CONSTRAINT form_details_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: form_pages_discovered form_pages_discovered_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.form_pages_discovered
    ADD CONSTRAINT form_pages_discovered_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: form_pages_discovered form_pages_discovered_crawl_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.form_pages_discovered
    ADD CONSTRAINT form_pages_discovered_crawl_session_id_fkey FOREIGN KEY (crawl_session_id) REFERENCES public.crawl_sessions(id) ON DELETE CASCADE;


--
-- Name: form_pages_discovered form_pages_discovered_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.form_pages_discovered
    ADD CONSTRAINT form_pages_discovered_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: networks networks_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.networks
    ADD CONSTRAINT networks_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id);


--
-- Name: networks networks_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.networks
    ADD CONSTRAINT networks_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: networks networks_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.networks
    ADD CONSTRAINT networks_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: networks networks_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.networks
    ADD CONSTRAINT networks_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: projects projects_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: projects projects_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: projects projects_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: screenshots screenshots_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.screenshots
    ADD CONSTRAINT screenshots_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: screenshots screenshots_crawl_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.screenshots
    ADD CONSTRAINT screenshots_crawl_session_id_fkey FOREIGN KEY (crawl_session_id) REFERENCES public.crawl_sessions(id) ON DELETE CASCADE;


--
-- Name: screenshots screenshots_form_page_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.screenshots
    ADD CONSTRAINT screenshots_form_page_id_fkey FOREIGN KEY (form_page_id) REFERENCES public.form_pages_discovered(id) ON DELETE CASCADE;


--
-- Name: screenshots screenshots_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.screenshots
    ADD CONSTRAINT screenshots_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: screenshots screenshots_uploaded_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.screenshots
    ADD CONSTRAINT screenshots_uploaded_by_user_id_fkey FOREIGN KEY (uploaded_by_user_id) REFERENCES public.users(id);


--
-- Name: users users_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: users users_created_by_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_created_by_admin_id_fkey FOREIGN KEY (created_by_admin_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

\unrestrict lJUb1q1B1u9xAaOidihfh6avDhDXPafaKOZtu2z6kNI2nvKkpjmj01PYBB4b1cC

