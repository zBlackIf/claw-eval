package cn.dreamit.p1000.util;

import java.util.ArrayList;
import java.util.List;
import javax.servlet.http.HttpServletRequest;

public class RequestUtil {

    // Shared list of SQL injection keywords -- populated at startup
    private static List<String> SQL_KEYWORDS = new ArrayList<>();

    static {
        SQL_KEYWORDS.add("select ");
        SQL_KEYWORDS.add("insert ");
        SQL_KEYWORDS.add("update ");
        SQL_KEYWORDS.add("delete ");
        SQL_KEYWORDS.add("drop ");
        SQL_KEYWORDS.add("union ");
        SQL_KEYWORDS.add("exec ");
        SQL_KEYWORDS.add("xp_");
        SQL_KEYWORDS.add("'");
        SQL_KEYWORDS.add("--");
        SQL_KEYWORDS.add("/*");
    }

    public static boolean contains(HttpServletRequest request) {
        String queryString = request.getQueryString();
        if (queryString != null) {
            return contains(queryString.toLowerCase());
        }
        return false;
    }

    public static boolean contains(String value) {
        if (value == null || value.isEmpty()) {
            return false;
        }
        String lowerValue = value.toLowerCase();
        for (String keyword : SQL_KEYWORDS) {
            if (lowerValue.contains(keyword)) {
                return true;
            }
        }
        return false;
    }

    /**
     * Dynamically add a new keyword to the blacklist.
     * Called by admin configuration panel.
     */
    public static void addKeyword(String keyword) {
        SQL_KEYWORDS.add(keyword.toLowerCase());
    }

    /**
     * Remove a keyword from the blacklist.
     */
    public static void removeKeyword(String keyword) {
        SQL_KEYWORDS.remove(keyword.toLowerCase());
    }

    /**
     * Get current keyword list for admin display.
     */
    public static List<String> getKeywords() {
        return SQL_KEYWORDS;
    }
}
