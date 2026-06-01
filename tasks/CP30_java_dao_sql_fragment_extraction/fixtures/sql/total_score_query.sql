-- total_score_query.sql
-- Base query for total score report.
-- The startedCourseSql and canTaketestSql JOIN fragments should be
-- incorporated here as conditional SQL (e.g., using MyBatis dynamic tags
-- or simple conditional includes).

SELECT
    studentinfo.id,
    studentinfo.Name,
    studentinfo.StudentNo,
    examstudentbooking.CourseVersionId,
    examstudentbooking.ExamBatchID
FROM studentinfo
INNER JOIN examstudentbooking
    ON examstudentbooking.StudentID = studentinfo.id

-- TODO: incorporate startedCourseSql JOIN here
-- TODO: incorporate canTaketestSql JOIN here

WHERE examstudentbooking.IsDelete = 0
    AND examstudentbooking.ExamBatchID = @ExamBatchID
