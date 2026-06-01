-- student_booking_list.sql
-- Used by another DAO method that also references the startedcourse
-- and examstudenttestqualification tables.

SELECT
    sb.StudentID,
    sb.ExamBatchID,
    sb.CourseVersionId,
    si.Name AS StudentName,
    si.StudentNo
FROM examstudentbooking sb
INNER JOIN studentinfo si ON si.id = sb.StudentID
WHERE sb.IsDelete = 0
    AND sb.ExamBatchID = @ExamBatchID
ORDER BY si.Name
