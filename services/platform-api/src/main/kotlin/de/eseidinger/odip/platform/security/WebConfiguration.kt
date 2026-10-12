package de.eseidinger.odip.platform.security

import org.springframework.context.annotation.Configuration
import org.springframework.web.servlet.config.annotation.InterceptorRegistry
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer

@Configuration
class WebConfiguration(
    private val platformPrincipalAuthorizationInterceptor: PlatformPrincipalAuthorizationInterceptor,
) : WebMvcConfigurer {
    override fun addInterceptors(registry: InterceptorRegistry) {
        registry.addInterceptor(platformPrincipalAuthorizationInterceptor).addPathPatterns("/api/**")
    }
}
