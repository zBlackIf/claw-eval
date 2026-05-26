package com.example.notify;

import com.example.model.Alarm;

public class EmailNotifier {
    private String smtpHost = "smtp.example.com";
    private int smtpPort = 587;

    public void send(Alarm alarm) {
        // hardcoded recipient
        String to = "admin@example.com";
        System.out.println("Sending email to " + to + ": " + alarm.getMessage());
    }
}
