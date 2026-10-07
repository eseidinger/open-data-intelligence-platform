package de.eseidinger.odip.platform.web

import jakarta.servlet.http.HttpServletRequest
import org.springframework.http.HttpStatus
import org.springframework.stereotype.Controller
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.server.ResponseStatusException

@Controller
class SpaController {
    @GetMapping("/", "/{path:[^\\.]*}")
    fun forwardToIndex(request: HttpServletRequest): String {
        val path = request.requestURI.removePrefix(request.contextPath)
        if (path == "/api" || path == "/actuator") {
            throw ResponseStatusException(HttpStatus.NOT_FOUND)
        }
        return "forward:/index.html"
    }
}
