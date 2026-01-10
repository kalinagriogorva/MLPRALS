from application.container import get_question_bank, get_minimum_levels
from ui.app_runner import run_ui

def main():
    run_ui(
        question_bank=get_question_bank(),
        minimum_levels=get_minimum_levels(),
    )

if __name__ == "__main__":
    main()
