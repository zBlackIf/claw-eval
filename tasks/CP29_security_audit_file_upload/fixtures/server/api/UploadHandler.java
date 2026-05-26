package com.orientdb.studio.api;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import org.apache.commons.fileupload.FileItem;
import org.apache.commons.fileupload.disk.DiskFileItemFactory;
import org.apache.commons.fileupload.servlet.ServletFileUpload;
import java.io.File;
import java.util.List;

public class UploadHandler {
    // VULNERABILITY: Upload directory inside web root
    private static final String UPLOAD_DIR = "uploads/";

    public void handleUpload(HttpServletRequest request,
                             HttpServletResponse response) throws Exception {
        if (!ServletFileUpload.isMultipartContent(request)) {
            response.sendError(400, "Not multipart");
            return;
        }

        DiskFileItemFactory factory = new DiskFileItemFactory();
        // VULNERABILITY: No file size limit configured
        ServletFileUpload upload = new ServletFileUpload(factory);

        List<FileItem> items = upload.parseRequest(request);
        for (FileItem item : items) {
            if (!item.isFormField()) {
                String fileName = item.getName();
                // VULNERABILITY: Using original filename without sanitization
                // Path traversal possible: ../../etc/passwd
                File uploadedFile = new File(UPLOAD_DIR + fileName);
                item.write(uploadedFile);
            }
        }
        response.setStatus(200);
    }
}
