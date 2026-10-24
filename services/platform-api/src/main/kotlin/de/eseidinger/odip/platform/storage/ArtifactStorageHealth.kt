package de.eseidinger.odip.platform.storage

import de.eseidinger.odip.platform.publication.PublicationError
import org.springframework.beans.factory.ObjectProvider
import org.springframework.boot.health.contributor.Health
import org.springframework.boot.health.contributor.HealthIndicator
import org.springframework.stereotype.Component

@Component("artifactStorage")
class ArtifactStorageHealth(private val stores: ObjectProvider<ObjectStore>) : HealthIndicator {
    override fun health(): Health = try {
        stores.ifAvailable?.check()
        Health.up().build()
    } catch (_: PublicationError) {
        // Never attach SDK exceptions or endpoint/credential details to health.
        Health.down().withDetail("code", "storage_unavailable").build()
    }
}
