package de.eseidinger.odip.platform.storage

import ch.qos.logback.classic.Level
import ch.qos.logback.classic.Logger
import ch.qos.logback.classic.spi.ILoggingEvent
import ch.qos.logback.core.read.ListAppender
import de.eseidinger.odip.platform.publication.PublicationError
import org.junit.jupiter.api.Test
import org.mockito.Mockito
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.support.DefaultListableBeanFactory
import org.springframework.jdbc.core.JdbcTemplate
import software.amazon.awssdk.services.s3.S3Client
import java.lang.reflect.Proxy
import java.util.UUID
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class StorageFailureTests {
    @Test fun `SDK failures never expose exception text or causes`() {
        val client = Proxy.newProxyInstance(S3Client::class.java.classLoader, arrayOf(S3Client::class.java)) { _, _, _ ->
            throw IllegalStateException("sensitive-token https://private-store payload")
        } as S3Client
        val store = S3ObjectStore(client, "bucket")
        val ref = ObjectReference("bucket", "key", "version", "0".repeat(64), 1)
        listOf<() -> Unit>({ store.put(byteArrayOf(1)) }, { store.read(ref) }, { store.delete(ref) }, { store.check() }).forEach { action ->
            val error = assertFailsWith<PublicationError> { action() }
            assertEquals(503, error.status)
            assertEquals("storage_unavailable", error.code)
            assertFalse(error.message.contains("sensitive-token"))
            assertNull(error.cause)
        }
    }

    @Test fun `cleanup retries log safe warning and successful lifecycle logs info`() {
        val jdbc = Mockito.mock(JdbcTemplate::class.java)
        val id = UUID.randomUUID()
        Mockito.`when`(jdbc.queryForList("SELECT * FROM artifact_object_deletion ORDER BY created_at LIMIT 100 FOR UPDATE SKIP LOCKED"))
            .thenReturn(listOf(mapOf("id" to id, "bucket" to "private-bucket", "object_key" to "private-key", "version_id" to "private-version")))
        var fail = true
        val fake = object : ObjectStore {
            override fun put(bytes: ByteArray): ObjectReference = error("unused")
            override fun read(reference: ObjectReference): ByteArray = error("unused")
            override fun check() = Unit
            override fun delete(reference: ObjectReference) {
                if (fail) throw PublicationError(503, "storage_unavailable", "sensitive-token")
            }
        }
        val beans = DefaultListableBeanFactory().also { it.registerSingleton("store", fake) }
        val cleanup = ArtifactObjectCleanup(jdbc, beans.getBeanProvider(ObjectStore::class.java))
        val logger = LoggerFactory.getLogger(ArtifactObjectCleanup::class.java) as Logger
        val events = ListAppender<ILoggingEvent>().also {
            it.start()
            logger.addAppender(it)
        }
        try {
            cleanup.clean()
            Mockito.verify(jdbc, Mockito.never()).update(Mockito.anyString(), Mockito.eq(id))
            assertEquals(Level.WARN, events.list.single().level)
            fail = false
            cleanup.clean()
            Mockito.verify(jdbc).update("DELETE FROM artifact_object_deletion WHERE id=?", id)
            assertEquals(Level.INFO, events.list.last().level)
            events.list.forEach { event ->
                assertNull(event.throwableProxy)
                val fields = event.keyValuePairs.associate { it.key to it.value }
                assertEquals(id, fields["operation_id"])
                assertTrue(fields.containsKey("elapsed_ms"))
                val serialized = event.formattedMessage + fields.toString()
                listOf("sensitive-token", "private-bucket", "private-key", "private-version").forEach { assertFalse(serialized.contains(it)) }
            }
        } finally {
            logger.detachAppender(events)
            events.stop()
        }
    }

    @Test fun `scheduled batch failures log safe errors without escaping to the scheduler`() {
        val cleanup = Mockito.mock(ArtifactObjectCleanup::class.java)
        Mockito.doThrow(IllegalStateException("sensitive-token SQL payload")).`when`(cleanup).clean()
        val logger = LoggerFactory.getLogger(ArtifactObjectCleanupSchedule::class.java) as Logger
        val events = ListAppender<ILoggingEvent>().also {
            it.start()
            logger.addAppender(it)
        }
        try {
            ArtifactObjectCleanupSchedule(cleanup).run()
            val event = events.list.single()
            assertEquals(Level.ERROR, event.level)
            assertNull(event.throwableProxy)
            assertFalse((event.formattedMessage + event.keyValuePairs.toString()).contains("sensitive-token"))
            assertEquals("artifact_cleanup_failed", event.keyValuePairs.single { it.key == "event" }.value)
        } finally {
            logger.detachAppender(events)
            events.stop()
        }
    }

    @Test fun `readiness is down without sensitive health details on storage failure`() {
        val fake = object : ObjectStore {
            override fun put(bytes: ByteArray): ObjectReference = error("unused")
            override fun read(reference: ObjectReference): ByteArray = error("unused")
            override fun delete(reference: ObjectReference) = Unit
            override fun check() = throw storageFailure("storage_unavailable")
        }
        val beans = DefaultListableBeanFactory().also { it.registerSingleton("store", fake) }
        val health = ArtifactStorageHealth(beans.getBeanProvider(ObjectStore::class.java)).health()
        assertEquals("DOWN", health.status.code)
        assertEquals(mapOf("code" to "storage_unavailable"), health.details)
    }
}
