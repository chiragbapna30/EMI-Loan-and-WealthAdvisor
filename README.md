# EMI and Loan Advisor Agent

## 1. Tools Named and Defined
* `compute_emi(amount, rate_annual, months)`: Calculates monthly installment payments (EMI), total repayable amount, and total interest accrued.
* `compare_options(options, monthly_income)`: Compares multiple loan choices side-by-side, applies the 40% EMI-to-income affordability rule, and identifies the option with the lowest total interest.

## 2. Memory Functionality
The agent utilizes session memory (`self.memory`) to retain key details across multiple user turns:
* **User Context:** Remembers the user's stated monthly income across questions so the user does not need to re-enter it.
* **Option History:** Stores all computed EMI choices during the conversation session to perform instant side-by-side comparative analyses when requested.

## 3. Honest Failure & Resolution
* **Failure:** Initially, when comparing a shorter high-EMI tenure with a longer low-EMI tenure, the agent recommended the lower EMI option strictly based on affordability, ignoring that the user would pay double the interest over time.
* **Handling:** Added total-interest calculation logic into `compare_options()` so the agent explicitly flags interest differences alongside monthly affordability.

## Group Contribution
* **Solo Project (100% Individual Ownership):** Built entirely by Chirag Bapna.
  * **Agent Architecture & Logic (`agent.py`):** Designed and implemented the complete core `EMILoanAgent` class, including the plan-act execution loop (`run_step`), state management (`self.memory`), and dynamic tool invocation routing (`execute_tool`).
  * **Tool Development:** Authored the underlying financial algorithms for `compute_emi` (compound interest calculation, total payment, interest accrued) and `compare_options` (40% income affordability threshold logic and lowest total interest sorting).
  * **Demonstration & Traces (`demo.ipynb`):** Structured and executed the multi-turn Jupyter Notebook demo to validate state persistence, plan-act decision paths, and clear tool call traces across consecutive turns.
  * **Documentation & Preparation:** Authored project documentation (`README.md`), verified all rubric guidelines, and structured the codebase for viva demonstration.