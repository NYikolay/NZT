import re


URL_PATTERN = re.compile(
    r"^https?://"  # Только HTTP/HTTPS
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
    r"localhost|"  # localhost
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # или IP
    r"(?::\d+)?"  # порт
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE | re.VERBOSE,
)

ENTITY_RELATIONS_EXTRACTION_PROMPT = """
    You are extracting memory entities.

    PERSON = specific human individual.
    ORGANIZATION = collective actor.
    PROJECT = effort being executed.
    PRODUCT = thing used or delivered.
    LOCATION = place.
    ASSET = owned resource with value.
    CONCEPT = abstract idea or field of knowledge.
    IDENTITY = self-definition or life role.
    GOAL = desired future outcome.

    Rules:

    PERSON vs IDENTITY:
    - John → PERSON
    - Founder → IDENTITY

    ORGANIZATION vs PRODUCT:
    - OpenAI → ORGANIZATION
    - ChatGPT → PRODUCT

    PROJECT vs GOAL:
    - Build startup → PROJECT
    - Reach $1M ARR → GOAL

    CONCEPT vs PRODUCT:
    - AI Agents → CONCEPT
    - ChatGPT → PRODUCT

    ASSET vs ORGANIZATION:
    - OpenAI → ORGANIZATION
    - OpenAI shares → ASSET
"""


SYSTEM_EXTRACTION_ENTITY_TYPE_CLASSIFICATION = """
Classification rules:

- PERSON = who
- ORGANIZATION = collective actor
- PROJECT = what is being executed
- PRODUCT = what is delivered or used
- LOCATION = where
- ASSET = what is owned
- CONCEPT = what is known or believed
- IDENTITY = who someone is
- GOAL = what is desired

Examples:

OpenAI -> ORGANIZATION
ChatGPT -> PRODUCT

My startup -> ORGANIZATION
Launching my startup -> PROJECT

Founder -> IDENTITY
John -> PERSON

Product Market Fit -> CONCEPT
Reach Product Market Fit -> GOAL

Apartment -> ASSET

Stockholm -> LOCATION
"""

ENTITY_TYPE_DESCRIPTIONS = {
    "PERSON": """
An individual human being.

Extract:
- People mentioned by name.
- Family members, friends, colleagues, investors, clients, mentors.
- Roles when they clearly refer to a specific person.

Examples:
- Anna
- my wife
- my CTO
- the investor
- John Smith

Do not extract:
- companies
- teams
- communities
""",
    "ORGANIZATION": """
A collective entity consisting of multiple people acting as a group.

Extract:
- Companies
- Startups
- Funds
- Universities
- Government institutions
- Teams
- Non-profits
- Communities

Examples:
- OpenAI
- Google
- Y Combinator
- Stanford University
- My startup

Do not extract:
- individual people
- products
- projects
""",
    "PROJECT": """
A temporary or ongoing initiative that evolves over time and has a purpose or outcome.

Extract:
- Business initiatives
- Fundraising rounds
- Research efforts
- Product launches
- Construction efforts
- Personal initiatives

Examples:
- Series A fundraising
- Building an AI assistant
- Apartment renovation
- Writing a book
- Website redesign

Do not extract:
- organizations
- goals without concrete execution
- products
""",
    "PRODUCT": """
A specific product, service, software application, platform, or offering that can be used, sold, consumed, or delivered.

Extract:
- Software products
- Apps
- SaaS products
- Physical products
- Services offered to customers

Examples:
- ChatGPT
- Notion
- iPhone
- Tesla Model Y
- Stripe

Do not extract:
- companies that own products
- abstract ideas
- projects
""",
    "LOCATION": """
A physical, geographical, or virtual place.

Extract:
- Cities
- Countries
- Regions
- Buildings
- Offices
- Homes
- Venues
- Online spaces if treated as locations

Examples:
- Stockholm
- Sweden
- My apartment
- The office
- San Francisco

Do not extract:
- organizations
- events
- projects
""",
    "ASSET": """
Something owned, controlled, managed, or having economic, strategic, or personal value.

Extract:
- Real estate
- Equity
- Stocks
- Bank accounts
- Domains
- Intellectual property
- Patents
- Vehicles
- Crypto wallets

Examples:
- My apartment
- 10% equity in the company
- Tesla shares
- openmemory.ai
- Bitcoin wallet

Do not extract:
- organizations
- products
- locations
""",
    "CONCEPT": """
An abstract idea, belief, theory, methodology, framework, technology area, or topic of knowledge.

Extract:
- Philosophies
- Mental models
- Scientific theories
- Technologies
- Methodologies
- Areas of study

Examples:
- Product Market Fit
- Stoicism
- AI Agents
- Machine Learning
- Game Theory

Do not extract:
- companies
- products
- people
""",
    "IDENTITY": """
A long-term self-definition describing who someone is or sees themselves as.

Extract:
- Personal identities
- Professional identities
- Social identities
- Life roles that define the person

Examples:
- Founder
- Entrepreneur
- Father
- Investor
- Engineer
- Immigrant

Do not extract:
- temporary job titles
- organizations
- specific people
""",
    "GOAL": """
A desired future outcome that someone intentionally wants to achieve.

Extract:
- Personal goals
- Business goals
- Financial goals
- Health goals
- Learning goals

Examples:
- Reach $1M ARR
- Lose 10 kg
- Raise a seed round
- Learn Spanish
- Buy a house

Do not extract:
- projects
- completed outcomes
- identities
""",
}
