package de.eseidinger.odip.platform.security

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import org.springframework.mock.web.MockHttpServletRequest
import org.springframework.mock.web.MockHttpServletResponse

class PlatformPrincipalAuthorizationInterceptorTests {
    private val interceptor = PlatformPrincipalAuthorizationInterceptor(
        PlatformAuthorizationProperties(
            userGroupIds = setOf("grp_e2987e192a0a41b4a0273c71c14fef47"),
            guestGroupIds = setOf("grp_8461fd4adec843d9be0d466a38fd564e"),
        ),
    )

    @Test
    fun `users can read and modify application data`() {
        assertTrue(interceptor.allows("GET", "grp_e2987e192a0a41b4a0273c71c14fef47"))
        assertTrue(interceptor.allows("POST", "grp_8461fd4adec843d9be0d466a38fd564e grp_e2987e192a0a41b4a0273c71c14fef47"))
    }

    @Test
    fun `guests can read but cannot modify application data`() {
        assertTrue(interceptor.allows("GET", "grp_8461fd4adec843d9be0d466a38fd564e"))
        assertFalse(interceptor.allows("POST", "grp_8461fd4adec843d9be0d466a38fd564e"))
    }

    @Test
    fun `the principal context is required`() {
        val request = MockHttpServletRequest("GET", "/api/data-sources")
        val response = MockHttpServletResponse()

        assertFalse(interceptor.preHandle(request, response, Any()))
        kotlin.test.assertEquals(401, response.status)
    }

    private fun PlatformPrincipalAuthorizationInterceptor.allows(method: String, groups: String): Boolean {
        val request = MockHttpServletRequest(method, "/api/data-sources")
        request.addHeader("X-Platform-Principal-Id", "prn_test")
        request.addHeader("X-Platform-Principal-Kind", "user")
        request.addHeader("X-Platform-Principal-Issuer", "https://identity.test")
        request.addHeader("X-Platform-Principal-Subject", "test-subject")
        request.addHeader("X-Platform-Principal-Group-Ids", groups)
        return preHandle(request, MockHttpServletResponse(), Any())
    }
}
