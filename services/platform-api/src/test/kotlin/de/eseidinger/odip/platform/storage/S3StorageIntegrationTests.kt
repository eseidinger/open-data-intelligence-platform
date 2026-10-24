package de.eseidinger.odip.platform.storage

import de.eseidinger.odip.platform.catalog.domain.DatasetEntity
import de.eseidinger.odip.platform.catalog.persistence.DatasetRepository
import de.eseidinger.odip.platform.publication.DatasetAccess
import de.eseidinger.odip.platform.publication.DraftRequest
import de.eseidinger.odip.platform.publication.PublicationContracts
import de.eseidinger.odip.platform.publication.PublicationError
import de.eseidinger.odip.platform.publication.PublicationService
import de.eseidinger.odip.platform.publication.RoutedArtifactStorage
import de.eseidinger.odip.platform.publication.ValidationReport
import de.eseidinger.odip.platform.publication.sha256
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc
import org.springframework.http.HttpHeaders
import org.springframework.http.MediaType
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.mock.web.MockHttpServletRequest
import org.springframework.test.context.DynamicPropertyRegistry
import org.springframework.test.context.DynamicPropertySource
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.content
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status
import org.springframework.transaction.annotation.Transactional
import software.amazon.awssdk.core.sync.RequestBody
import software.amazon.awssdk.services.s3.S3Client
import java.util.UUID
import kotlin.test.assertContentEquals
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

@SpringBootTest(properties = ["odip.artifact-storage.backend=s3", "odip.authorization.require-principal-context=true"])
@EnabledIfEnvironmentVariable(named = "ODIP_S3_INTEGRATION_TEST", matches = "true")
@AutoConfigureMockMvc
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@Transactional
class S3StorageIntegrationTests {
    @Autowired private lateinit var entityManager: jakarta.persistence.EntityManager

    @Autowired private lateinit var mvc: MockMvc

    @Autowired private lateinit var client: S3Client

    @Autowired private lateinit var store: ObjectStore

    @Autowired private lateinit var storage: RoutedArtifactStorage

    @Autowired private lateinit var migration: ArtifactMigration

    @Autowired private lateinit var cleanup: ArtifactObjectCleanup

    @Autowired private lateinit var jdbc: JdbcTemplate

    @Autowired private lateinit var datasets: DatasetRepository

    @Autowired private lateinit var access: DatasetAccess

    @Autowired private lateinit var service: PublicationService

    @Autowired private lateinit var contracts: PublicationContracts

    companion object {
        private val bucket = "odip-test-${UUID.randomUUID()}"

        @JvmStatic
        @DynamicPropertySource
        fun properties(registry: DynamicPropertyRegistry) {
            registry.add("S3_BUCKET") { bucket }
        }
    }

    @BeforeAll fun createBucket() {
        client.createBucket { it.bucket(bucket) }
        client.putBucketVersioning { it.bucket(bucket).versioningConfiguration { config -> config.status("Enabled") } }
    }

    @AfterAll fun removeOwnedBucket() {
        client.listObjectVersionsPaginator { it.bucket(bucket) }.forEach { page ->
            page.versions().forEach { version -> client.deleteObject { it.bucket(bucket).key(version.key()).versionId(version.versionId()) } }
            page.deleteMarkers().forEach { version -> client.deleteObject { it.bucket(bucket).key(version.key()).versionId(version.versionId()) } }
        }
        client.deleteBucket { it.bucket(bucket) }
    }

    private fun principal(name: String) = MockHttpServletRequest().also {
        it.addHeader("X-Platform-Principal-Id", name)
        it.addHeader("X-Platform-Principal-Kind", "service")
        it.addHeader("X-Platform-Principal-Issuer", "https://identity.test")
        it.addHeader("X-Platform-Principal-Subject", name)
        it.addHeader("X-Platform-Principal-Client-Id", "client-$name")
        it.addHeader("X-Platform-Principal-Group-Ids", "grp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    }
    private fun headers(name: String) = HttpHeaders().also { headers ->
        val request = principal(name)
        request.headerNames.toList().forEach { headers.add(it, request.getHeader(it)) }
    }
    private val fixtureName = "non-energy-mobility-counts-2024"
    private fun fixture(path: String) = javaClass.getResourceAsStream("/contract-fixtures/$fixtureName/$path")!!.readAllBytes()

    private fun draft(): UUID {
        val dataset = datasets.saveAndFlush(DatasetEntity(name = "S3 ${UUID.randomUUID()}"))
        listOf("READ", "WRITE").forEach { access.grant(dataset.id, "writer", it) }
        access.grant(dataset.id, "validator", "VALIDATE")
        access.grant(dataset.id, "reader", "READ")
        @Suppress("UNCHECKED_CAST")
        val manifest = contracts.mapper.readValue(fixture("manifest.json"), Map::class.java) as Map<String, Any?>
        return service.create(principal("writer"), DraftRequest(dataset.id, manifest), UUID.randomUUID().toString())["id"] as UUID
    }

    private fun publish(id: UUID) {
        service.publish(principal("writer"), id, "publish-$id")
        val job = service.claim(principal("validator"))!!
        assertEquals(id, job["id"])
        val manifest = contracts.parse(fixture("manifest.json"))
        val policy = contracts.policy(manifest)
        service.complete(principal("validator"), id, ValidationReport(job["manifestSha256"].toString(), policy["policyRef"].asText(), policy["checks"].associate { it.asText() to "PASS" }, manifest["artifacts"].associate { it["artifactId"].asText() to it["sha256"].asText() }, claimToken = job["claimToken"] as UUID))
    }

    private fun capturedRaw(): Pair<UUID, ByteArray> {
        val source = UUID.randomUUID()
        val run = UUID.randomUUID()
        val raw = UUID.randomUUID()
        val bytes = "captured raw bytes".toByteArray()
        val dataset = datasets.saveAndFlush(DatasetEntity(name = "Raw ${UUID.randomUUID()}"))
        jdbc.update("INSERT INTO data_source(id,name,source_type,location,owner,license) VALUES (?,?,'API','https://github.com/fixture','Fixture','CC-BY-4.0')", source, "S3 fixture $source")
        jdbc.update("INSERT INTO dataset_source VALUES (?,?)", dataset.id, source)
        jdbc.update("INSERT INTO pipeline_run(id,pipeline_name,source_id,status) VALUES (?,'fixture',?,'SUCCEEDED')", run, source)
        jdbc.update("INSERT INTO raw_artifact(id,pipeline_run_id,source_id,storage_uri,payload,content_length,checksum_sha256,retrieved_at) VALUES (?,?,?,'postgres://fixture',?,?,?,CURRENT_TIMESTAMP)", raw, run, source, bytes, bytes.size, sha256(bytes))
        listOf("READ", "INGEST").forEach { access.grant(dataset.id, "writer", it) }
        return raw to bytes
    }

    @Test fun `UI migration capabilities require S3 and the same permissions as migration`() {
        val publication = draft()
        val (raw, _) = capturedRaw()
        val dataset = jdbc.queryForObject("SELECT dataset_id FROM dataset_publication WHERE id=?", UUID::class.java, publication)
        val source = jdbc.queryForObject("SELECT source_id FROM raw_artifact WHERE id=?", UUID::class.java, raw)
        mvc.perform(get("/api/v1/operator-capabilities").headers(headers("writer")))
            .andExpect(status().isOk)
            .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath("$.artifactStorage.enabled").value(true))
            .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath("$.artifactStorage.publicationDatasetIds").value(org.hamcrest.Matchers.hasItem(dataset.toString())))
            .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath("$.artifactStorage.sourceIds").value(org.hamcrest.Matchers.hasItem(source.toString())))
        mvc.perform(get("/api/v1/operator-capabilities").headers(headers("reader")))
            .andExpect(status().isOk)
            .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath("$.artifactStorage.publicationDatasetIds").isEmpty)
            .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath("$.artifactStorage.sourceIds").isEmpty)
    }

    @Test fun `direct S3 publication retains consumer contract and permissions`() {
        val id = draft()
        val manifest = contracts.parse(fixture("manifest.json"))
        manifest["artifacts"].forEach {
            val artifact = it["artifactId"].asText()
            service.upload(principal("writer"), id, artifact, fixture("artifacts/$artifact.json"))
        }
        assertEquals(0, jdbc.queryForObject("SELECT count(*) FROM publication_artifact WHERE publication_id=? AND payload IS NOT NULL", Int::class.java, id))
        publish(id)
        assertContentEquals(fixture("manifest.json"), service.read(principal("reader"), fixtureName, "1.0.0", null).first)
        manifest["artifacts"].forEach {
            val artifact = it["artifactId"].asText()
            assertContentEquals(fixture("artifacts/$artifact.json"), service.read(principal("reader"), fixtureName, "1.0.0", artifact).first)
        }
        assertEquals(403, assertFailsWith<PublicationError> { service.read(principal("unapproved"), fixtureName, "1.0.0", "hourly-counts") }.status)
    }

    @Test fun `published PostgreSQL artifact migrates without changing manifest bytes or database copy`() {
        val id = draft()
        val bytes = fixture("artifacts/hourly-counts.json")
        jdbc.update("INSERT INTO publication_artifact(publication_id,artifact_id,payload,sha256,content_length) VALUES (?,'hourly-counts',?,?,?)", id, bytes, sha256(bytes), bytes.size)
        publish(id)
        assertEquals(403, assertFailsWith<PublicationError> { migration.publication(principal("reader"), id, "hourly-counts", true) }.status)
        assertEquals("ready", migration.publication(principal("writer"), id, "hourly-counts", false)["status"])
        assertEquals(0, jdbc.queryForObject("SELECT count(*) FROM artifact_object WHERE publication_id=?", Int::class.java, id))
        assertEquals("migrated", migration.publication(principal("writer"), id, "hourly-counts", true)["status"])
        assertEquals("already_migrated", migration.publication(principal("writer"), id, "hourly-counts", true)["status"])
        assertContentEquals(bytes, jdbc.queryForObject("SELECT payload FROM publication_artifact WHERE publication_id=?", ByteArray::class.java, id))
        assertContentEquals(fixture("manifest.json"), service.read(principal("reader"), fixtureName, "1.0.0", null).first)
        assertContentEquals(bytes, service.read(principal("reader"), fixtureName, "1.0.0", "hourly-counts").first)
        // A fresh storage instance models the reference lookup after restart.
        val providers = org.springframework.beans.factory.support.DefaultListableBeanFactory().also { it.registerSingleton("objects", store) }
        assertContentEquals(bytes, RoutedArtifactStorage(jdbc, providers.getBeanProvider(ObjectStore::class.java), "s3").read(id, "hourly-counts"))
    }

    @Test fun `raw migration preserves lineage and does not fall back after losing an exact version`() {
        val (id, bytes) = capturedRaw()
        assertEquals(403, assertFailsWith<PublicationError> { migration.raw(principal("reader"), id, true) }.status)
        val publication = draft()
        jdbc.update("INSERT INTO dataset_source SELECT p.dataset_id,r.source_id FROM dataset_publication p,raw_artifact r WHERE p.id=? AND r.id=?", publication, id)
        jdbc.update("INSERT INTO publication_input VALUES (?,?)", publication, id)
        service.upload(principal("writer"), publication, "hourly-counts", fixture("artifacts/hourly-counts.json"))
        publish(publication)
        val before = jdbc.queryForMap("SELECT * FROM raw_artifact WHERE id=?", id)
        assertEquals("migrated", migration.raw(principal("writer"), id, true)["status"])
        assertContentEquals(bytes, storage.readRaw(id))
        val after = jdbc.queryForMap("SELECT * FROM raw_artifact WHERE id=?", id)
        before.filterKeys { it != "payload" }.forEach { (key, value) -> assertEquals(value, after[key]) }
        val ref = jdbc.queryForMap("SELECT * FROM artifact_object WHERE raw_artifact_id=?", id)
        client.deleteObject { it.bucket(bucket).key(ref["object_key"] as String).versionId(ref["version_id"] as String) }
        assertEquals(503, assertFailsWith<PublicationError> { storage.readRaw(id) }.status)
        assertContentEquals(bytes, jdbc.queryForObject("SELECT payload FROM raw_artifact WHERE id=?", ByteArray::class.java, id))
    }

    @Test fun `raw ingestion uses S3 and completion retry retains exact content`() {
        val (existing, _) = capturedRaw()
        val source = jdbc.queryForObject("SELECT source_id FROM raw_artifact WHERE id=?", UUID::class.java, existing)
        val queued = mvc.perform(post("/api/data-sources/$source/ingestions").headers(headers("writer"))).andExpect(status().isAccepted).andReturn()
        entityManager.flush()
        val run = contracts.parse(queued.response.contentAsByteArray)["id"].asText()
        val started = mvc.perform(post("/api/pipeline-runs/$run/started").headers(headers("writer"))).andExpect(status().isOk).andReturn()
        val token = contracts.parse(started.response.contentAsByteArray)["claimToken"].asText()
        val body = """{"claimToken":"$token","payload":"e30=","contentType":"application/json","contentLength":2,"checksumSha256":"${sha256("{}".toByteArray())}"}"""
        repeat(2) {
            mvc.perform(post("/api/pipeline-runs/$run/completed").headers(headers("writer")).contentType(MediaType.APPLICATION_JSON).content(body)).andExpect(status().isOk)
        }
        val raw = jdbc.queryForMap("SELECT id,payload FROM raw_artifact WHERE pipeline_run_id=?", UUID.fromString(run))
        assertNull(raw["payload"])
        mvc.perform(get("/api/raw-artifacts/${raw["id"]}/content").headers(headers("writer"))).andExpect(status().isOk).andExpect(content().bytes("{}".toByteArray()))
        mvc.perform(get("/api/raw-artifacts/${raw["id"]}/content").headers(headers("reader"))).andExpect(status().isForbidden)
    }

    @Test fun `rolling back a migrated reference retains the database source`() {
        val (id, bytes) = capturedRaw()
        jdbc.execute(
            org.springframework.jdbc.core.ConnectionCallback { connection ->
                val savepoint = connection.setSavepoint()
                migration.raw(principal("writer"), id, true)
                assertEquals(1, jdbc.queryForObject("SELECT count(*) FROM artifact_object WHERE raw_artifact_id=?", Int::class.java, id))
                connection.rollback(savepoint)
                connection.releaseSavepoint(savepoint)
            },
        )
        assertEquals(0, jdbc.queryForObject("SELECT count(*) FROM artifact_object WHERE raw_artifact_id=?", Int::class.java, id))
        assertContentEquals(bytes, storage.readRaw(id))
    }

    @Test fun `pinned object version survives later writes and integrity failures are closed`() {
        val bytes = "immutable".toByteArray()
        val reference = store.put(bytes)
        client.putObject({ it.bucket(bucket).key(reference.key) }, RequestBody.fromString("new bytes"))
        assertContentEquals(bytes, store.read(reference))
        assertEquals("storage_integrity_failed", assertFailsWith<PublicationError> { store.read(reference.copy(digest = "0".repeat(64))) }.code)
        assertEquals("storage_integrity_failed", assertFailsWith<PublicationError> { store.read(reference.copy(length = 1)) }.code)
        assertEquals("storage_reference_invalid", assertFailsWith<PublicationError> { store.read(reference.copy(bucket = "another-bucket")) }.code)
    }

    @Test fun `unversioned target rejects migration and retains original without a new reference`() {
        val (id, bytes) = capturedRaw()
        client.putBucketVersioning { it.bucket(bucket).versioningConfiguration { config -> config.status("Suspended") } }
        try {
            assertEquals("storage_versioning_required", assertFailsWith<PublicationError> { migration.raw(principal("writer"), id, true) }.code)
            assertNull(jdbc.queryForList("SELECT storage_id FROM artifact_object WHERE raw_artifact_id=?", id).firstOrNull())
            assertContentEquals(bytes, storage.readRaw(id))
        } finally {
            client.putBucketVersioning { it.bucket(bucket).versioningConfiguration { config -> config.status("Enabled") } }
        }
    }

    @Test fun `expiry deletes only the retained S3 version through the transactional outbox`() {
        val id = draft()
        service.upload(principal("writer"), id, "hourly-counts", fixture("artifacts/hourly-counts.json"))
        publish(id)
        val ref = jdbc.queryForMap("SELECT * FROM artifact_object WHERE publication_id=?", id)
        val replacement = client.putObject({ it.bucket(bucket).key(ref["object_key"] as String) }, RequestBody.fromString("other version"))
        assertNotEquals(ref["version_id"], replacement.versionId())
        jdbc.update("INSERT INTO publication_support VALUES ('urn:portfolio:mobility-counts:v1',CURRENT_TIMESTAMP - INTERVAL '2 years')")
        service.recoverAbandoned()
        assertTrue(jdbc.queryForList("SELECT * FROM artifact_object WHERE publication_id=?", id).isEmpty())
        assertEquals(1, jdbc.queryForObject("SELECT count(*) FROM artifact_object_deletion WHERE version_id=?", Int::class.java, ref["version_id"]))
        cleanup.clean()
        assertEquals(0, jdbc.queryForObject("SELECT count(*) FROM artifact_object_deletion WHERE version_id=?", Int::class.java, ref["version_id"]))
        assertEquals("other version", client.getObjectAsBytes { it.bucket(bucket).key(ref["object_key"] as String).versionId(replacement.versionId()) }.asUtf8String())
    }
}
