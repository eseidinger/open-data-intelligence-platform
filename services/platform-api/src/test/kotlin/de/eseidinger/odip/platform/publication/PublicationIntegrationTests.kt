package de.eseidinger.odip.platform.publication

import de.eseidinger.odip.platform.catalog.domain.DatasetEntity
import de.eseidinger.odip.platform.catalog.persistence.DatasetRepository
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.mock.web.MockHttpServletRequest
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.*
import org.springframework.transaction.annotation.Transactional
import org.springframework.http.MediaType
import java.util.UUID
import kotlin.test.*

@SpringBootTest(properties=["odip.authorization.require-principal-context=true"])
@AutoConfigureMockMvc
@Transactional
class PublicationIntegrationTests(@Autowired private val service: PublicationService, @Autowired private val contracts: PublicationContracts,
    @Autowired private val access: DatasetAccess, @Autowired private val datasets: DatasetRepository,
    @Autowired private val mvc: MockMvc, @Autowired private val jdbc: JdbcTemplate) {
    private fun principal(name: String) = MockHttpServletRequest().also {
        it.addHeader("X-Platform-Principal-Id", name); it.addHeader("X-Platform-Principal-Kind", "service")
        it.addHeader("X-Platform-Principal-Issuer", "https://identity.test"); it.addHeader("X-Platform-Principal-Subject", name)
        it.addHeader("X-Platform-Principal-Client-Id", "client-$name")
        it.addHeader("X-Platform-Principal-Group-Ids", "grp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    }
    private fun fixture(path: String) = javaClass.getResourceAsStream("/contract-fixtures/$path")!!.readAllBytes()
    private fun prepare(name: String): Triple<UUID, UUID, Map<String, Any?>> {
        val dataset = datasets.saveAndFlush(DatasetEntity(name="Publication ${UUID.randomUUID()}"))
        listOf("READ", "WRITE").forEach { access.grant(dataset.id, "writer", it) }
        access.grant(dataset.id, "validator", "VALIDATE"); access.grant(dataset.id, "reader", "READ")
        @Suppress("UNCHECKED_CAST") val manifest = contracts.mapper.readValue(fixture("$name/manifest.json"), Map::class.java) as Map<String, Any?>
        val draft = service.create(principal("writer"), DraftRequest(dataset.id, manifest), "draft-$name")
        val id = draft["id"] as UUID
        contracts.parse(fixture("$name/manifest.json"))["artifacts"].forEach { descriptor ->
            val artifact = descriptor["artifactId"].asText()
            service.upload(principal("writer"), id, artifact, fixture("$name/artifacts/$artifact.json"))
        }
        return Triple(id, dataset.id, manifest)
    }
    private fun finish(id: UUID, pass: Boolean = true): ValidationReport {
        service.publish(principal("writer"), id, "publish-$id")
        val job = service.claim(principal("validator"))!!
        assertEquals(id, job["id"])
        val manifest = contracts.parse(contracts.mapper.writeValueAsBytes(job["manifest"]))
        val policy = contracts.policy(manifest)
        val report = ValidationReport(job["manifestSha256"].toString(), policy["policyRef"].asText(),
            policy["checks"].associate { it.asText() to if(pass) "PASS" else "FAIL" },
            manifest["artifacts"].associate { it["artifactId"].asText() to it["sha256"].asText() }, if(pass) null else "profile_validation_failed", job["claimToken"] as UUID)
        service.complete(principal("validator"), id, report)
        return report
    }

    @Test fun `both shared fixtures publish and retain exact canonical bytes`() {
        for (name in listOf("energy-reference-wasserburg-am-inn-2024", "non-energy-mobility-counts-2024")) {
            val (id, _, _) = prepare(name)
            assertEquals(409, assertFailsWith<PublicationError> { service.read(principal("reader"), name, "1.0.0", null) }.status)
            finish(id)
            assertContentEquals(fixture("$name/manifest.json"), service.read(principal("reader"), name, "1.0.0", null).first)
            val etag = "\"${sha256(fixture("$name/manifest.json"))}\""
            mvc.perform(get("/api/v1/datasets/$name/versions/1.0.0").headers(org.springframework.http.HttpHeaders().also { headers ->
                listOf("Id" to "reader", "Kind" to "service", "Issuer" to "https://identity.test", "Subject" to "reader", "Client-Id" to "client-reader", "Group-Ids" to "grp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa").forEach { headers.add("X-Platform-Principal-${it.first}",it.second) }
            }).header("If-None-Match",etag)).andExpect(status().isNotModified).andExpect(header().string("ETag",etag))
        }
    }

    @Test fun `failed validation never becomes readable and retry returns recorded outcome`() {
        val (id, _, _) = prepare("non-energy-mobility-counts-2024")
        val report = finish(id, false)
        assertEquals("FAILED", service.complete(principal("validator"), id, report)["status"])
        assertEquals(409, assertFailsWith<PublicationError> { service.read(principal("reader"), "non-energy-mobility-counts-2024", "1.0.0", null) }.status)
        assertEquals(403, assertFailsWith<PublicationError> { service.complete(principal("writer"), id, report) }.status)
    }

    @Test fun `permissions protect discovery writes and legacy routes`() {
        val (id, _, _) = prepare("non-energy-mobility-counts-2024")
        finish(id)
        assertEquals(0L, service.discover(principal("unapproved"),null,0,20)["total"])
        assertEquals(403, assertFailsWith<PublicationError> { service.read(principal("unapproved"), "non-energy-mobility-counts-2024", "1.0.0",null) }.status)
        assertEquals(403, assertFailsWith<PublicationError> { service.publish(principal("reader"),id,"reader-write") }.status)
        mvc.perform(get("/api/v1/datasets")).andExpect(status().isUnauthorized)
        mvc.perform(get("/api/raw-artifacts/${UUID.randomUUID()}/content").header("X-Platform-Principal-Id","reader").header("X-Platform-Principal-Kind","service").header("X-Platform-Principal-Issuer","https://identity.test").header("X-Platform-Principal-Subject","reader").header("X-Platform-Principal-Client-Id","client-reader").header("X-Platform-Principal-Group-Ids","grp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")).andExpect(status().isForbidden)
    }

    @Test fun `grants on a zero UUID dataset cannot bypass other publication permissions`() {
        val (id, _, _) = prepare("non-energy-mobility-counts-2024")
        val zero = datasets.saveAndFlush(DatasetEntity(id=UUID(0,0), name="Zero UUID ${UUID.randomUUID()}"))
        access.grant(zero.id, "unapproved", "READ")
        access.grant(zero.id, "unapproved", "VALIDATE")
        service.publish(principal("writer"), id, "publish-$id")
        assertNull(service.claim(principal("unapproved")))
        finish(id)
        assertEquals(0L, service.discover(principal("unapproved"),null,0,20)["total"])
    }

    @Test fun `idempotency pins body and artifact corruption is rejected`() {
        val name = "non-energy-mobility-counts-2024"
        val (id, dataset, manifest) = prepare(name)
        assertEquals(id, service.create(principal("writer"),DraftRequest(dataset,manifest),"draft-$name")["id"])
        assertEquals(409, assertFailsWith<PublicationError> { service.create(principal("writer"),DraftRequest(dataset,manifest + ("version" to "1.0.1")),"draft-$name") }.status)
        assertEquals("checksum_mismatch", assertFailsWith<PublicationError> { service.upload(principal("writer"),id,"hourly-counts","{}".toByteArray()) }.code)
        finish(id)
        assertEquals(409, assertFailsWith<PublicationError> { service.upload(principal("writer"),id,"hourly-counts",fixture("$name/artifacts/hourly-counts.json")) }.status)
    }

    @Test fun `new versions and catalog edits preserve old publication bytes`() {
        val name = "non-energy-mobility-counts-2024"
        val (id, dataset, manifest) = prepare(name)
        finish(id)
        jdbc.update("UPDATE dataset SET owner='Changed owner' WHERE id=?",dataset)
        assertContentEquals(fixture("$name/manifest.json"),service.read(principal("reader"),name,"1.0.0",null).first)
        val next = service.create(principal("writer"),DraftRequest(dataset,manifest + ("version" to "1.0.1")),"correction")
        assertNotEquals(id,next["id"])
        assertEquals(409,assertFailsWith<PublicationError> { service.read(principal("reader"),name,"1.0.1",null) }.status)
    }

    @Test fun `database guards reject published mutation`() {
        val (id, _, _) = prepare("non-energy-mobility-counts-2024")
        finish(id)
        assertFailsWith<org.springframework.dao.DataAccessException> { jdbc.update("UPDATE dataset_publication SET manifest='bad'::bytea WHERE id=?",id) }
    }

    @Test fun `published lineage protects the captured input bytes`() {
        val (id,dataset,_) = prepare("non-energy-mobility-counts-2024")
        val source=UUID.randomUUID(); val run=UUID.randomUUID(); val raw=UUID.randomUUID()
        val bytes=fixture("non-energy-mobility-counts-2024/artifacts/hourly-counts.json")
        jdbc.update("INSERT INTO data_source(id,name,source_type,location,owner,license) VALUES (?,?,'API','https://github.com/fixture','Fixture','CC-BY-4.0')",source,"Raw fixture $source")
        jdbc.update("INSERT INTO dataset_source VALUES (?,?)",dataset,source)
        jdbc.update("INSERT INTO pipeline_run(id,pipeline_name,source_id,status) VALUES (?,'fixture',?,'SUCCEEDED')",run,source)
        jdbc.update("INSERT INTO raw_artifact(id,pipeline_run_id,source_id,storage_uri,payload,content_length,checksum_sha256,retrieved_at) VALUES (?,?,?,'postgres://fixture',?,?,?,CURRENT_TIMESTAMP)",raw,run,source,bytes,bytes.size,sha256(bytes))
        jdbc.update("INSERT INTO publication_input VALUES (?,?)",id,raw)
        finish(id)
        assertEquals(1,(service.draft(principal("writer"),id)["inputArtifacts"] as List<*>).size)
        assertFailsWith<org.springframework.dao.DataAccessException> { jdbc.update("UPDATE raw_artifact SET payload='changed'::bytea WHERE id=?",raw) }
    }

    @Test fun `schemas reject unknown majors and duplicate keys`() {
        assertEquals("invalid_json",assertFailsWith<PublicationError> { contracts.parse("{\"a\":1,\"a\":2}".toByteArray()) }.code)
        val name = "non-energy-mobility-counts-2024"
        val (_, dataset, manifest) = prepare(name)
        assertEquals("schema_validation_failed",assertFailsWith<PublicationError> { service.create(principal("writer"),DraftRequest(dataset,manifest + ("schemaVersion" to "dataset-publication/v2")),"unsupported") }.code)
    }

    @Test fun `abandoned claims are replaced and stale evidence cannot publish`() {
        val (id, _, _) = prepare("non-energy-mobility-counts-2024")
        service.publish(principal("writer"),id,"recover")
        val old = service.claim(principal("validator"))!!
        jdbc.update("UPDATE dataset_publication SET claimed_at=CURRENT_TIMESTAMP - INTERVAL '6 minutes' WHERE id=?",id)
        service.recoverAbandoned()
        val current = service.claim(principal("validator"))!!
        assertNotEquals(old["claimToken"],current["claimToken"])
        val report = ValidationReport(old["manifestSha256"].toString(),"urn:portfolio:mobility-counts-quality:v1",mapOf(),mapOf(),claimToken=old["claimToken"] as UUID)
        assertEquals("stale_claim",assertFailsWith<PublicationError> { service.complete(principal("validator"),id,report) }.code)
    }

    @Test fun `retention preserves supported versions and expires only after grace`() {
        val (id, _, _) = prepare("non-energy-mobility-counts-2024")
        finish(id)
        jdbc.update("INSERT INTO publication_support VALUES ('urn:portfolio:mobility-counts:v1',CURRENT_TIMESTAMP + INTERVAL '1 day')")
        service.recoverAbandoned()
        assertContentEquals(fixture("non-energy-mobility-counts-2024/manifest.json"),service.read(principal("reader"),"non-energy-mobility-counts-2024","1.0.0",null).first)
        jdbc.update("UPDATE publication_support SET support_ends_at=CURRENT_TIMESTAMP - INTERVAL '2 years'")
        service.recoverAbandoned()
        assertEquals(404,assertFailsWith<PublicationError> { service.read(principal("reader"),"non-energy-mobility-counts-2024","1.0.0",null) }.status)
    }
}
