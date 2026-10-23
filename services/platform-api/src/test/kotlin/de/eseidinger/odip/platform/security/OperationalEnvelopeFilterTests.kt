package de.eseidinger.odip.platform.security

import jakarta.servlet.FilterChain
import org.slf4j.MDC
import org.springframework.mock.web.MockHttpServletRequest
import org.springframework.mock.web.MockHttpServletResponse
import java.io.ByteArrayOutputStream
import java.io.PrintStream
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class OperationalEnvelopeFilterTests {
    @Test
    fun `request context is available downstream and restored after failure`() {
        val correlation = "12345678-1234-1234-1234-123456789abc"
        val request = MockHttpServletRequest("GET", "/api/private-location")
        request.addHeader("X-Correlation-Id", correlation)
        val response = MockHttpServletResponse()
        MDC.put("correlationId", "outer-context")
        try {
            val output = capture {
                assertFailsWith<IllegalStateException> {
                    OperationalEnvelopeFilter().doFilter(
                        request,
                        response,
                        FilterChain { _, _ ->
                            assertEquals(correlation, MDC.get("correlationId"))
                            throw IllegalStateException("private-token")
                        },
                    )
                }
            }
            assertEquals(correlation, response.getHeader("X-Correlation-Id"))
            assertEquals("outer-context", MDC.get("correlationId"))
            assertTrue(output.contains("\"level\":\"error\""))
            assertTrue(output.contains("\"status\":500"))
            assertTrue(Regex("\"durationMs\":\\d+").containsMatchIn(output))
            assertEquals(1, output.trim().lines().size)
            assertFalse(output.contains("private-token"))
            assertFalse(output.contains("private-location"))
        } finally {
            MDC.remove("correlationId")
        }
    }

    @Test
    fun `untrusted correlation header is replaced and context cleaned after client error`() {
        val request = MockHttpServletRequest("POST", "/api/datasets")
        request.addHeader("X-Correlation-Id", "private-token\nforged-log")
        val response = MockHttpServletResponse()
        val output = capture {
            OperationalEnvelopeFilter().doFilter(request, response, FilterChain { _, _ -> response.status = 403 })
        }
        assertTrue(Regex("[a-f0-9-]{36}").matches(response.getHeader("X-Correlation-Id").orEmpty()))
        assertEquals(null, MDC.get("correlationId"))
        assertTrue(output.contains("\"level\":\"warning\""))
        assertTrue(output.contains("\"status\":403"))
        assertFalse(output.contains("private-token"))
    }

    private fun capture(block: () -> Unit): String {
        val original = System.out
        val bytes = ByteArrayOutputStream()
        try {
            System.setOut(PrintStream(bytes))
            block()
        } finally {
            System.setOut(original)
        }
        return bytes.toString(Charsets.UTF_8)
    }
}
