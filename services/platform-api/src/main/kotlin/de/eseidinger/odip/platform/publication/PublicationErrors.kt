package de.eseidinger.odip.platform.publication

import org.springframework.dao.DataIntegrityViolationException
import org.springframework.http.ResponseEntity
import org.springframework.http.converter.HttpMessageNotReadableException
import org.springframework.web.bind.MissingRequestHeaderException
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.bind.annotation.RestControllerAdvice
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException

@RestControllerAdvice
class PublicationErrors {
    @ExceptionHandler(PublicationError::class)
    fun error(error: PublicationError) = ResponseEntity.status(error.status).body(mapOf("schemaVersion" to "error/v1", "status" to error.status, "code" to error.code, "message" to error.message))

    @ExceptionHandler(DataIntegrityViolationException::class)
    fun conflict() = error(PublicationError(409, "conflict", "The operation conflicts with existing immutable data"))

    @ExceptionHandler(HttpMessageNotReadableException::class, MissingRequestHeaderException::class, MethodArgumentTypeMismatchException::class)
    fun invalid(error: Exception): ResponseEntity<out Map<String, Any>> {
        var cause: Throwable? = error
        while (cause != null) {
            if (cause is PublicationError) return error(cause)
            cause = cause.cause
        }
        return error(PublicationError(400, "invalid_request", "Malformed request or missing required header"))
    }
}
