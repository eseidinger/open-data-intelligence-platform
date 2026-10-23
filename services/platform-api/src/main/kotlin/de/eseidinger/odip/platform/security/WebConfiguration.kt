package de.eseidinger.odip.platform.security

import org.springframework.context.annotation.Configuration
import org.springframework.web.servlet.config.annotation.InterceptorRegistry
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer

@Configuration
class WebConfiguration(
    private val platformPrincipalAuthorizationInterceptor: PlatformPrincipalAuthorizationInterceptor,
    private val legacyObjectAuthorization: LegacyObjectAuthorization,
) : WebMvcConfigurer {
    override fun addInterceptors(registry: InterceptorRegistry) {
        registry.addInterceptor(platformPrincipalAuthorizationInterceptor).addPathPatterns("/api/**")
        registry.addInterceptor(legacyObjectAuthorization).addPathPatterns("/api/**")
    }
    override fun addResourceHandlers(registry: ResourceHandlerRegistry) {
        registry.addResourceHandler("/ui/**").addResourceLocations("classpath:/static/")
    }
}
