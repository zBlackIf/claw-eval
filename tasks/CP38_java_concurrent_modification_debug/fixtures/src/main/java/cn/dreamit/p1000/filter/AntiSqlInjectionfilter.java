package cn.dreamit.p1000.filter;

import cn.dreamit.p1000.util.RequestUtil;

import javax.servlet.*;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Enumeration;
import java.util.Map;

public class AntiSqlInjectionfilter implements Filter {

    @Override
    public void init(FilterConfig filterConfig) throws ServletException {
        // no-op
    }

    @Override
    public void doFilter(ServletRequest servletRequest, ServletResponse servletResponse,
                         FilterChain filterChain) throws IOException, ServletException {
        HttpServletRequest request = (HttpServletRequest) servletRequest;
        HttpServletResponse response = (HttpServletResponse) servletResponse;

        // Check query string
        if (RequestUtil.contains(request)) {
            response.sendError(HttpServletResponse.SC_FORBIDDEN, "Illegal request parameters detected");
            return;
        }

        // Check all parameter values
        Map<String, String[]> parameterMap = request.getParameterMap();
        for (Map.Entry<String, String[]> entry : parameterMap.entrySet()) {
            String[] values = entry.getValue();
            if (values != null) {
                for (String value : values) {
                    if (RequestUtil.contains(value)) {
                        response.sendError(HttpServletResponse.SC_FORBIDDEN,
                                "Illegal parameter value detected in: " + entry.getKey());
                        return;
                    }
                }
            }
        }

        // Check headers
        Enumeration<String> headerNames = request.getHeaderNames();
        while (headerNames.hasMoreElements()) {
            String headerName = headerNames.nextElement();
            String headerValue = request.getHeader(headerName);
            if (headerValue != null && RequestUtil.contains(headerValue)) {
                response.sendError(HttpServletResponse.SC_FORBIDDEN,
                        "Illegal header value detected in: " + headerName);
                return;
            }
        }

        filterChain.doFilter(servletRequest, servletResponse);
    }

    @Override
    public void destroy() {
        // no-op
    }
}
