package com.orientdb.studio.api;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.*;

public class ETLHandler {
    private static final String ETL_DIR = "/opt/orientdb/etl/";

    public void handleETLUpload(HttpServletRequest request,
                                 HttpServletResponse response) throws Exception {
        String contentType = request.getContentType();
        // PARTIAL CHECK: Only checks content-type header (easily spoofed)
        if (contentType == null || !contentType.contains("application/json")) {
            response.sendError(400, "Only JSON files accepted");
            return;
        }

        BufferedReader reader = request.getReader();
        StringBuilder body = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            body.append(line);
        }

        // VULNERABILITY: No validation of JSON content
        // Could contain malicious ETL commands
        String filename = request.getParameter("name");
        if (filename == null) filename = "etl_config.json";
        // VULNERABILITY: filename from user input, no sanitization
        FileWriter writer = new FileWriter(ETL_DIR + filename);
        writer.write(body.toString());
        writer.close();

        response.setStatus(200);
    }
}
