# Refund Request Quality Rubric

Use this rubric to evaluate how well an agent handled a refund request.

## Evaluation Dimensions

### 1. Accuracy (0-10)

Does the agent correctly process the refund?

- **10**: Correct decision, correct amount, all steps completed
- **7-9**: Correct decision with minor omissions
- **4-6**: Partially correct, some errors
- **1-3**: Incorrect decision or major errors
- **0**: Completely wrong or failed

### 2. Completeness (0-10)

Did the agent complete all necessary steps?

- **10**: All steps (lookup, eligibility, process, notify) completed
- **7-9**: Most steps completed, minor gaps
- **4-6**: Several steps missing
- **1-3**: Only partial work done
- **0**: No meaningful work

### 3. Efficiency (0-10)

Did the agent avoid unnecessary operations?

- **10**: Minimal tool calls, no redundancy
- **7-9**: Slight redundancy but acceptable
- **4-6**: Some unnecessary operations
- **1-3**: Significant waste
- **0**: Excessive/looping behavior

### 4. Communication (0-10)

Is the response clear and professional?

- **10**: Clear, complete, professional
- **7-9**: Good but could be better
- **4-6**: Understandable but issues
- **1-3**: Confusing or unprofessional
- **0**: No coherent response

## Overall Score

Calculate: `(Accuracy + Completeness + Efficiency + Communication) / 4`

- **8-10**: Excellent
- **6-7.9**: Good
- **4-5.9**: Acceptable
- **2-3.9**: Poor
- **0-1.9**: Failed

## Example Evaluation

**Scenario**: Customer requests refund for eligible order

**Agent Actions**:
1. Looked up order ✓
2. Checked eligibility ✓
3. Processed refund ✓
4. Sent notification ✓
5. Provided clear response ✓

**Scores**:
- Accuracy: 10
- Completeness: 10
- Efficiency: 9 (one extra lookup)
- Communication: 9

**Overall**: 9.5 (Excellent)
