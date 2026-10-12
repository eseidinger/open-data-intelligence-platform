package de.eseidinger.odip.platform.security

import jakarta.servlet.FilterChain
import jakarta.servlet.ReadListener
import jakarta.servlet.ServletInputStream
import jakarta.servlet.http.HttpServletRequest
import jakarta.servlet.http.HttpServletRequestWrapper
import jakarta.servlet.http.HttpServletResponse
import de.eseidinger.odip.platform.publication.PublicationError
import org.springframework.stereotype.Component
import org.springframework.web.filter.OncePerRequestFilter

@Component
class BoundedRequestFilter : OncePerRequestFilter() {
    override fun doFilterInternal(request: HttpServletRequest, response: HttpServletResponse, chain: FilterChain) {
        if (!request.requestURI.startsWith("/api/")) { chain.doFilter(request, response); return }
        val limit = if (request.requestURI.contains("/artifacts/") && request.method == "PUT") 10485760L else 14680064L
        if (request.contentLengthLong > limit || request.getHeader("Content-Encoding")?.let { it != "identity" } == true) {
            response.status = 413
            response.contentType = "application/json"
            response.writer.write("""{"schemaVersion":"error/v1","status":413,"code":"payload_too_large","message":"Request exceeds the decoded body limit or uses unsupported compression"}""")
            return
        }
        val wrapped = object : HttpServletRequestWrapper(request) {
            private val bounded by lazy {
                val input = request.inputStream
                object : ServletInputStream() {
                    var count = 0L
                    fun checked(size: Int): Int { if (size > 0) count += size; if (count > limit) throw PublicationError(413,"payload_too_large","Request exceeds the body limit"); return size }
                    override fun read(): Int { val value = input.read(); if (value >= 0) checked(1); return value }
                    override fun read(bytes: ByteArray, offset: Int, length: Int) = checked(input.read(bytes, offset, length))
                    override fun isFinished() = input.isFinished
                    override fun isReady() = input.isReady
                    override fun setReadListener(listener: ReadListener) = input.setReadListener(listener)
                }
            }
            override fun getInputStream(): ServletInputStream = bounded
        }
        chain.doFilter(wrapped, response)
    }
}
