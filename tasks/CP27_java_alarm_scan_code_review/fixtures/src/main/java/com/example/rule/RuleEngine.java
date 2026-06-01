package com.example.rule;

import java.util.*;
import com.example.model.Metric;
import com.example.model.Rule;

public class RuleEngine {
    public List<Rule> rules = new ArrayList<>();  // should be private

    public Rule evaluate(Metric metric) {
        for (Rule r : rules) {
            try {
                if (r.getThreshold() < metric.getValue()) {
                    return r;
                }
            } catch (Exception e) {
                // silently swallowed
            }
        }
        return null;
    }

    public void addRule(Rule r) {
        rules.add(r);
    }
}
