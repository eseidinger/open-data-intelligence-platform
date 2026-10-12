package de.eseidinger.odip.platform.security

import de.eseidinger.odip.platform.publication.checkPublication
import org.springframework.beans.factory.annotation.Value
import org.springframework.stereotype.Component
import java.net.URI

@Component
class SourcePolicy(@Value("\${odip.source-policy.enabled:true}") private val enabled: Boolean,
    @Value("\${odip.source-policy.hosts:jsonplaceholder.typicode.com,ec.europa.eu,re.jrc.ec.europa.eu}") hosts: String) {
    private val allowed = hosts.split(',').map { it.trim() }.toSet()
    fun check(location: String) {
        if (!enabled) return
        val uri = runCatching { URI(location) }.getOrNull()
        checkPublication(uri != null && uri.scheme == "https" && uri.host in allowed && uri.port in setOf(-1,443) && uri.userInfo == null && uri.fragment == null,
            "source_destination_denied", "Source must use an approved HTTPS host", 400)
    }
}
