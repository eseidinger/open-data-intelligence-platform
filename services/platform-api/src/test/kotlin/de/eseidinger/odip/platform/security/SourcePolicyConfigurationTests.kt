package de.eseidinger.odip.platform.security

import de.eseidinger.odip.platform.publication.PublicationError
import org.junit.jupiter.api.Assertions.assertDoesNotThrow
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test
import org.springframework.boot.env.YamlPropertySourceLoader
import org.springframework.boot.test.context.runner.ApplicationContextRunner
import org.springframework.core.env.StandardEnvironment
import org.springframework.core.env.SystemEnvironmentPropertySource
import org.springframework.core.io.FileSystemResource

class SourcePolicyConfigurationTests {
    private val fixtureUrl = "https://github.com/eseidinger/energy-system-configuration/releases/tag/contract-kit-v0.4.0"

    private fun runner(hosts: String? = null) = ApplicationContextRunner()
        .withInitializer { context ->
            val environment = if (hosts == null) emptyMap<String, Any>() else mapOf<String, Any>("ODIP_SOURCE_HOSTS" to hosts)
            context.environment.propertySources.replace(
                StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME,
                SystemEnvironmentPropertySource(StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME, environment),
            )
            // Load the production configuration, not the test application.yml that disables source policy.
            YamlPropertySourceLoader().load("production-application", FileSystemResource("src/main/resources/application.yml"))
                .forEach { context.environment.propertySources.addLast(it) }
        }
        .withUserConfiguration(SourcePolicy::class.java)

    private fun assertDenied(policy: SourcePolicy, location: String) {
        val error = assertThrows(PublicationError::class.java) { policy.check(location) }
        assertEquals(400, error.status)
        assertEquals("source_destination_denied", error.code)
    }

    @Test
    fun `environment allowlist permits the reference fixture source`() {
        runner("github.com, ec.europa.eu").run { context ->
            val policy = context.getBean(SourcePolicy::class.java)
            assertDoesNotThrow { policy.check(fixtureUrl) }
            assertDoesNotThrow { policy.check("https://ec.europa.eu/reference") }
            assertDenied(policy, "https://unapproved.example/reference")
        }
    }

    @Test
    fun `missing environment allowlist retains restrictive defaults`() {
        runner().run { context ->
            val policy = context.getBean(SourcePolicy::class.java)
            for (host in listOf("jsonplaceholder.typicode.com", "ec.europa.eu", "re.jrc.ec.europa.eu")) {
                assertDoesNotThrow { policy.check("https://$host/reference") }
            }
            assertDenied(policy, fixtureUrl)
        }
    }

    @Test
    fun `environment allowlist replaces defaults rather than broadening them`() {
        runner("approved.example").run { context ->
            val policy = context.getBean(SourcePolicy::class.java)
            assertDoesNotThrow { policy.check("https://approved.example/reference") }
            assertDenied(policy, "https://jsonplaceholder.typicode.com/reference")
            assertDenied(policy, fixtureUrl)
        }
    }

    @Test
    fun `configured hosts still require safe HTTPS locations`() {
        runner("github.com").run { context ->
            val policy = context.getBean(SourcePolicy::class.java)
            for (location in listOf(
                "http://github.com/reference",
                "https://github.com:8443/reference",
                "https://user@github.com/reference",
                "https://github.com/reference#fragment",
                "https://github.com.unapproved.example/reference",
                "https://127.0.0.1/reference",
            )) {
                assertDenied(policy, location)
            }
        }
    }

    @Test
    fun `explicit Spring property takes precedence over environment alias`() {
        runner("github.com").withPropertyValues("odip.source-policy.hosts=override.example").run { context ->
            val policy = context.getBean(SourcePolicy::class.java)
            assertDoesNotThrow { policy.check("https://override.example/reference") }
            assertDenied(policy, fixtureUrl)
        }
    }

    @Test
    fun `empty environment allowlist denies all sources`() {
        runner("").run { context ->
            val policy = context.getBean(SourcePolicy::class.java)
            assertDenied(policy, fixtureUrl)
            assertDenied(policy, "https://jsonplaceholder.typicode.com/reference")
        }
    }
}
