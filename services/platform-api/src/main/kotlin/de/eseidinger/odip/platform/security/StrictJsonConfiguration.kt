package de.eseidinger.odip.platform.security

import org.springframework.boot.jackson.autoconfigure.JsonFactoryBuilderCustomizer
import org.springframework.boot.jackson.autoconfigure.JsonMapperBuilderCustomizer
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import tools.jackson.core.StreamReadFeature
import tools.jackson.databind.DeserializationFeature

@Configuration
class StrictJsonConfiguration {
    @Bean fun duplicateKeys() = JsonFactoryBuilderCustomizer { it.enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION) }

    @Bean fun requestFields() = JsonMapperBuilderCustomizer { it.enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES) }
}
