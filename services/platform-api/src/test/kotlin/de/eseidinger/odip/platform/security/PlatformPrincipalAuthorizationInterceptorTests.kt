package de.eseidinger.odip.platform.security

import org.springframework.mock.web.MockHttpServletRequest
import org.springframework.mock.web.MockHttpServletResponse
import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class PlatformPrincipalAuthorizationInterceptorTests {
    private val interceptor = PlatformPrincipalAuthorizationInterceptor(PlatformAuthorizationProperties())

    @Test
    fun `legacy and versioned routes trust platform authorization without repeating group checks`() {
        for (path in listOf("/api/data-sources", "/api/pipeline-runs/claim-next", "/api/v1/datasets", "/api/v1/dataset-grants")) {
            for (method in listOf("GET", "POST", "PUT", "DELETE")) {
                assertTrue(interceptor.allows(method, "grp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", path))
                assertTrue(interceptor.allows(method, "grp_8461fd4adec843d9be0d466a38fd564e grp_e2987e192a0a41b4a0273c71c14fef47", path))
            }
        }
    }

    @Test
    fun `group headers must retain the platform format but do not define local roles`() {
        for (groups in listOf("", "guests", "grp_malformed", "grp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa  grp_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")) {
            assertFalse(interceptor.allows("GET", groups))
        }
    }

    @Test
    fun `the principal context is required`() {
        val request = MockHttpServletRequest("GET", "/api/data-sources")
        val response = MockHttpServletResponse()

        assertFalse(interceptor.preHandle(request, response, Any()))
        kotlin.test.assertEquals(401, response.status)
    }

    @Test
    fun `malformed duplicate and incomplete service context is denied`() {
        for (mutation in listOf<(MockHttpServletRequest) -> Unit>(
            { it.addHeader("X-Platform-Principal-Id", "prn_duplicate") },
            { it.removeHeader("X-Platform-Principal-Group-Ids") },
            { it.addHeader("X-Platform-Principal-Kind", "service") },
        )) {
            val request = MockHttpServletRequest("GET", "/api/v1/datasets")
            request.addHeader("X-Platform-Principal-Id", "prn_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
            request.addHeader("X-Platform-Principal-Kind", "user")
            request.addHeader("X-Platform-Principal-Issuer", "https://identity.test")
            request.addHeader("X-Platform-Principal-Subject", "subject")
            request.addHeader("X-Platform-Principal-Group-Ids", "grp_e2987e192a0a41b4a0273c71c14fef47")
            mutation(request)
            val response = MockHttpServletResponse()
            assertFalse(interceptor.preHandle(request, response, Any()))
            kotlin.test.assertEquals(401, response.status)
        }
    }

    private fun PlatformPrincipalAuthorizationInterceptor.allows(method: String, groups: String, path: String = "/api/data-sources"): Boolean {
        val request = MockHttpServletRequest(method, path)
        request.addHeader("X-Platform-Principal-Id", "prn_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        request.addHeader("X-Platform-Principal-Kind", "user")
        request.addHeader("X-Platform-Principal-Issuer", "https://identity.test")
        request.addHeader("X-Platform-Principal-Subject", "test-subject")
        request.addHeader("X-Platform-Principal-Group-Ids", groups)
        return preHandle(request, MockHttpServletResponse(), Any())
    }
}
