package com.example.examination.dao.totalscore;

import java.util.HashMap;
import java.util.Map;

public class TotalScoreDao {

    /**
     * Build common query parameters for total score queries.
     * The startedCourseSql and canTaketestSql fragments are currently
     * built inline in Java. They should be moved to SQL templates.
     */
    public QueryParams getQueryCommonParams(Context context, TotalScoreCondition data, String courseFromTableName) {
        Map<String, Object> params = new HashMap<>();
        StringBuilder sqlBuilder = new StringBuilder();

        // Base query
        sqlBuilder.append("SELECT studentinfo.id, studentinfo.Name, studentinfo.StudentNo, ");
        sqlBuilder.append("examstudentbooking.CourseVersionId, examstudentbooking.ExamBatchID ");
        sqlBuilder.append("FROM studentinfo ");
        sqlBuilder.append("INNER JOIN examstudentbooking ON examstudentbooking.StudentID = studentinfo.id ");

        // ---- startedCourseSql: dynamic JOIN based on UpToStandard filter ----
        String startedCourseSql = " ";
        if (!(StringHelper.isNullOrBlank(data.getUpToStandard()) || "-1".equals(data.getUpToStandard()))) {
            startedCourseSql = " INNER JOIN startedcourse ON startedcourse.StudentID = studentinfo.id "
                    + "AND startedcourse.CourseVersionID = examstudentbooking.CourseVersionId "
                    + "AND startedcourse.STATUS IN (1, 2) AND startedcourse.IsDelete = 0 "
                    + "AND startedcourse.DataStatus = 1 AND startedcourse.UpToStandard = @UpToStandard";
            params.put("UpToStandard", data.getUpToStandard());
        }

        // ---- canTaketestSql: dynamic JOIN based on CanTakeTest filter ----
        String canTaketestSql = " ";
        if (!(StringHelper.isNullOrBlank(data.getCanTakeTest()) || "-1".equals(data.getCanTakeTest()))) {
            canTaketestSql = " INNER JOIN examstudenttestqualification "
                    + "ON examstudenttestqualification.ExamBatchID = examstudentbooking.ExamBatchID "
                    + "AND examstudenttestqualification.StudentID = examstudentbooking.StudentID "
                    + "AND examstudenttestqualification.CourseVersionId = examstudentbooking.CourseVersionId "
                    + "AND examstudenttestqualification.IsDelete = 0 "
                    + "AND examstudenttestqualification.CanTakeTest = @CanTakeTest";
            params.put("CanTakeTest", data.getCanTakeTest());
        }

        sqlBuilder.append(startedCourseSql);
        sqlBuilder.append(canTaketestSql);

        // Course table join
        if (courseFromTableName != null && !courseFromTableName.isEmpty()) {
            sqlBuilder.append(" INNER JOIN ").append(courseFromTableName)
                    .append(" ON ").append(courseFromTableName)
                    .append(".CourseVersionID = examstudentbooking.CourseVersionId");
        }

        // WHERE clause
        sqlBuilder.append(" WHERE examstudentbooking.IsDelete = 0 ");
        sqlBuilder.append("AND examstudentbooking.ExamBatchID = @ExamBatchID ");
        params.put("ExamBatchID", data.getExamBatchId());

        if (!StringHelper.isNullOrBlank(data.getStudentName())) {
            sqlBuilder.append("AND studentinfo.Name LIKE @StudentName ");
            params.put("StudentName", "%" + data.getStudentName() + "%");
        }

        if (!StringHelper.isNullOrBlank(data.getStudentNo())) {
            sqlBuilder.append("AND studentinfo.StudentNo = @StudentNo ");
            params.put("StudentNo", data.getStudentNo());
        }

        return new QueryParams(sqlBuilder.toString(), params);
    }
}
