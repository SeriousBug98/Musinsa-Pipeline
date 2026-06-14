package com.musinsa.processor.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import jakarta.servlet.Filter;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Bean
    public FilterRegistrationBean<Filter> removeXFrameOptions() {
        FilterRegistrationBean<Filter> bean = new FilterRegistrationBean<>();
        bean.setFilter((request, response, chain) -> {
            ((jakarta.servlet.http.HttpServletResponse) response)
                .setHeader("X-Frame-Options", "SAMEORIGIN");
            chain.doFilter(request, response);
        });
        bean.addUrlPatterns("/*");
        return bean;
    }
}
