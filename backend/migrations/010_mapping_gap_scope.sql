DELETE FROM semantic_observations AS mapping
USING semantic_observations AS classification, dpp_documents AS document
WHERE mapping.observation_type = 'mapping_missing'
  AND classification.document_id = mapping.document_id
  AND classification.term_iri = mapping.term_iri
  AND classification.observation_type = 'term_classification'
  AND document.document_id = mapping.document_id
  AND (
      classification.category = 'unknown'
      OR (
          classification.category = 'custom'
          AND split_part(split_part(mapping.term_iri, '://', 2), '.', 1)
              = lower(document.organisation_id)
      )
  );
