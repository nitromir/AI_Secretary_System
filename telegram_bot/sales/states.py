"""FSM states for the sales funnel.

When state is None (cleared), the user is in normal AI chat mode.
Any SalesFunnel.* state means the user is in the sales funnel.
"""

from aiogram.fsm.state import State, StatesGroup


class SalesFunnel(StatesGroup):
    # Onboarding
    welcome = State()
    quiz_tech = State()
    quiz_infra = State()

    # DIY Path
    diy_audit = State()
    diy_audit_custom = State()  # free-text GPU input
    diy_result = State()
    diy_github = State()

    # Basic Path
    basic_value = State()
    basic_demo = State()
    basic_checkout = State()
    basic_no_gpu = State()

    # Custom Path
    custom_intro = State()
    custom_step_1 = State()  # free-text: describe task
    custom_step_2 = State()  # choice: volume
    custom_step_3 = State()  # multi-choice: integrations
    custom_step_4 = State()  # choice: timeline
    custom_step_5 = State()  # choice: budget
    custom_quote = State()
    custom_expensive = State()

    # TZ (Technical Specification) Path
    tz_start = State()
    tz_project_type = State()  # choice: what type of project
    tz_project_desc = State()  # free-text: describe the project
    tz_business_goal = State()  # choice: business goal
    tz_features = State()  # free-text: key features
    tz_timeline = State()  # choice: timeline
    tz_budget = State()  # choice: budget
    tz_contact = State()  # free-text: contact info
    tz_generating = State()  # waiting for AI to generate TZ
    tz_result = State()  # TZ generated, showing result

    # Idle within sales context
    idle = State()
