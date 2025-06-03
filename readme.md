# PlexTech Applicant Portal - Backend

Welcome to the backend application of the PlexTech applicant portal. 
This readme only provides a high-level overview of the entire project; for more details, refer to comments within the main Python file. 

For the frontend repository, please visit [this link](https://github.com/bradley-tian/plextech-application-frontend).

## Data Storage and Persistence

The backend API server is connected with a MongoDB cluster to support the storage and processing of applicant data. A NoSQL fashion is chosen for the flexibility in storing dynamic forms of data - text-based, file-base, image-based, etc. 

To make updates on MongoDB connections, reconfigure the connection string as well as collection names as listed throughout the Python file. 

## Leadership Roster and Semantics

Manually-configured information, which include the administrator roster, year translations, and response evaluation weights are listed near the top of the Python file and should be inspected every semester. 

## Application Assignment

Applications are assigned to each grader via a weighted round-robin approach. If needed, the redundancy threshold should be updated prior to assignment each semester.

The overall goal is to guarantee a baseline number of leadership officers and total graders per applicant, as specified by the redundancy metrics. Below is a detailed walkthrough of the assignment process. 

1. Each grader is classified as either a 'member' or 'leadership.' A grader cannot be both.
2. Each grader class corresponds to its own mod space (total number of graders in its class).
3. Initialize pointers for both member and leadership lists. 
4. Iterate through every applicant in the database. For each applicant, perform the same cycle for both members and leadership officers: assigned the grader currently pointed to by the corresponding pointer to the applicant, and advance the pointer; repeat this sequence for as many time as dictated by the redundancy metrics. 
5. Iterate through every applicant again, this time assigning the applicant to each grader that was associated with this applicant in the iteration in step 4. This ensure a double record on both the applicant and grader side.

## Evaluation of Results

The overall goal is to standardize each grader's response to each individual criterion based on their own harshness for that criterion. For example, if Alice tends to grade criterion A very harshly, then applicants graded by Alice that have a low score in criterion A will be penalized less; on the other hand, applicants who receive a high score from Alice for that criterion will be outstandingly rewarded. Below is a more detailed walkthrough of the evaluation algorithm. 

1. Assmeble the 'judgments' dictionary keyed on graders; each grader key corresponds to an inner dictionary keyed on each criterion, with each criterion's value being a list of (applicant ID, score) tuples. This dictionary represents the grader's grading behaviors, reflecting their judgments on the applicants per each criterion. 
2. For each grader, Iterate through the criteria - there should be exactly ten total. For each criterion, iterate through the list of tuples, standardizing each applicant's raw score with respect to the mean of all applicants reviewed by this grader. Criterion 0 (r0), which corresponds to the time commitment question, is reviewed separately; the score is simply divided evenly, as it does not reflect a subjective evaluation. 
3. Assemble the 'evaluations' dictionary keyed on applicant ID; each applicant key corresponds to an inner dictionary keyed on each criterion, with each criterion's value being a list of all the standardized scores that applicant has received from their graders for that criterion.
4. Iterate through each applicant in the 'evaluations' dictionary, reducing each applicant's list of scores down to the average of all their scores for each criterion. 
5. Iterate through each applicant once again, this time filling in their personal information into 'evaluations' using their profiles from the database. Then for each criterion, proceed to compute an addition to the applicant's total score based on their average standardized score and the weight on that criterion. To handle unexpected errors, any invalid computation is converted into 0.02, which is about the global mean. 
6. (This section has been frequently revised) apply any bonus points based on graduation year and other personal factors to the applicant's total score. 
7. Compile the evaluations data and generate a CSV file as the response. 
