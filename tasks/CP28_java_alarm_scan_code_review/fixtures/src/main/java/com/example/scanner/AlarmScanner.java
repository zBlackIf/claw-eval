package com.example.scanner;

import java.util.List;
import java.util.ArrayList;
import com.example.model.Metric;
import com.example.model.Alarm;
import com.example.rule.RuleEngine;
import com.example.classifier.AlarmClassifier;

public class AlarmScanner {
    private RuleEngine ruleEngine;
    private AlarmClassifier classifier;
    private List<Metric> metrics = new ArrayList<>();

    public AlarmScanner(RuleEngine re, AlarmClassifier ac) {
        this.ruleEngine = re;
        this.classifier = ac;
    }

    // TODO: should be an interface
    public List<Alarm> scan() {
        List<Alarm> alarms = new ArrayList<>();
        for (Metric m : metrics) {
            var matched = ruleEngine.evaluate(m);
            if (matched != null) {
                Alarm a = new Alarm();
                a.setLevel(classifier.classify(m, matched));
                a.setMessage(m.getName() + " triggered");
                a.setTimestamp(System.currentTimeMillis());
                alarms.add(a);
            }
        }
        return alarms;
    }

    public void addMetric(Metric m) {
        metrics.add(m);
    }
}
