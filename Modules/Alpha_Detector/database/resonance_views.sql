-- Database Views for Resonance-Enhanced Scoring
-- These views implement the mathematical resonance equations and enhanced scoring

-- View for resonance-enhanced scores
CREATE OR REPLACE VIEW v_resonance_enhanced_scores AS
SELECT 
    s.id,
    s.sig_sigma,
    s.sig_confidence,
    s.accumulated_score,
    s.phi,
    s.rho,
    s.telemetry->>'surprise' as surprise,
    s.telemetry->>'sr' as success_rate,
    s.telemetry->>'cr' as confirmation_rate,
    s.telemetry->>'xr' as contradiction_rate,
    
    -- Current enhanced scoring (already built)
    (s.sig_sigma * 0.4 + s.sig_confidence * 0.3 + s.accumulated_score * 0.3) as current_score,
    
    -- Resonance score from MotifCard
    (s.phi * s.rho * COALESCE((s.telemetry->>'surprise')::float, 0.0)) as resonance_score,
    
    -- Enhanced final score with resonance boost
    (s.sig_sigma * 0.4 + s.sig_confidence * 0.3 + s.accumulated_score * 0.3) * 
    (1 + (s.phi * s.rho * COALESCE((s.telemetry->>'surprise')::float, 0.0)) * 0.2) as final_score,
    
    -- Resonance field strength
    (s.phi * s.rho) as field_strength,
    
    -- Resonance quality metrics
    CASE 
        WHEN s.phi > 0.8 AND s.rho > 1.2 THEN 'high_resonance'
        WHEN s.phi > 0.5 AND s.rho > 1.0 THEN 'medium_resonance'
        WHEN s.phi > 0.2 AND s.rho > 0.8 THEN 'low_resonance'
        ELSE 'no_resonance'
    END as resonance_quality,
    
    s.created_at,
    s.updated_at
FROM AD_strands s
WHERE s.kind = 'motif'
    AND s.created_at >= NOW() - INTERVAL '24 hours'
ORDER BY final_score DESC;

-- View for resonance rates calculation
CREATE OR REPLACE VIEW v_resonance_rates AS
SELECT 
    motif_id,
    motif_name,
    motif_family,
    
    -- Success rate calculation
    AVG(CASE WHEN accumulated_score > 0 THEN 1.0 ELSE 0.0 END) as success_rate,
    
    -- Confirmation rate calculation
    AVG(CASE WHEN sig_confidence > 0.7 THEN 1.0 ELSE 0.0 END) as confirmation_rate,
    
    -- Contradiction rate calculation
    AVG(CASE WHEN accumulated_score < -0.5 THEN 1.0 ELSE 0.0 END) as contradiction_rate,
    
    -- Surprise rate calculation (based on rarity)
    CASE 
        WHEN COUNT(*) = 1 THEN 1.0
        WHEN COUNT(*) < 5 THEN 0.8
        WHEN COUNT(*) < 20 THEN 0.5
        ELSE 0.2
    END as surprise_rate,
    
    -- Total occurrences
    COUNT(*) as total_occurrences,
    
    -- Average metrics
    AVG(sig_sigma) as avg_sigma,
    AVG(sig_confidence) as avg_confidence,
    AVG(accumulated_score) as avg_outcome,
    
    -- Time range
    MIN(created_at) as first_occurrence,
    MAX(created_at) as last_occurrence
    
FROM AD_strands
WHERE kind = 'motif'
    AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY motif_id, motif_name, motif_family
HAVING COUNT(*) >= 5  -- Minimum samples for reliable rates
ORDER BY success_rate DESC, total_occurrences DESC;

-- View for resonance field analysis
CREATE OR REPLACE VIEW v_resonance_field_analysis AS
SELECT 
    motif_family,
    regime,
    session_bucket,
    
    -- Family-level resonance metrics
    AVG(phi) as avg_phi,
    AVG(rho) as avg_rho,
    AVG(phi * rho) as avg_field_strength,
    
    -- Family-level performance metrics
    AVG(COALESCE((telemetry->>'sr')::float, 0.0)) as avg_success_rate,
    AVG(COALESCE((telemetry->>'cr')::float, 0.0)) as avg_confirmation_rate,
    AVG(COALESCE((telemetry->>'xr')::float, 0.0)) as avg_contradiction_rate,
    AVG(COALESCE((telemetry->>'surprise')::float, 0.0)) as avg_surprise,
    
    -- Count metrics
    COUNT(*) as motif_count,
    COUNT(DISTINCT motif_id) as unique_motifs,
    
    -- Resonance quality distribution
    COUNT(CASE WHEN phi > 0.8 AND rho > 1.2 THEN 1 END) as high_resonance_count,
    COUNT(CASE WHEN phi > 0.5 AND rho > 1.0 THEN 1 END) as medium_resonance_count,
    COUNT(CASE WHEN phi > 0.2 AND rho > 0.8 THEN 1 END) as low_resonance_count,
    
    -- Time metrics
    MIN(created_at) as first_occurrence,
    MAX(created_at) as last_occurrence,
    MAX(phi_updated_at) as last_phi_update,
    MAX(rho_updated_at) as last_rho_update
    
FROM AD_strands
WHERE kind = 'motif'
    AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY motif_family, regime, session_bucket
ORDER BY avg_field_strength DESC;

-- View for resonance-enhanced experiment queue (using AD_strands)
CREATE OR REPLACE VIEW v_resonance_experiment_queue AS
SELECT 
    e.id as candidate_id,
    e.motif_id,
    e.motif_family as family,
    e.prioritization_score as resonance_score,
    ROW_NUMBER() OVER (PARTITION BY e.motif_family ORDER BY e.prioritization_score DESC) as cap_rank,
    e.created_at,
    
    -- Hypothesis details (from same strand)
    e.mechanism_hypothesis as hypothesis_text,
    e.experiment_shape,
    e.experiment_grammar->>'success_metric' as success_metric,
    e.experiment_grammar->>'min_samples' as min_samples,
    e.experiment_grammar->>'ttl_hours' as ttl_hours,
    
    -- Motif details (from same strand)
    e.motif_name,
    e.motif_family,
    e.phi,
    e.rho,
    e.telemetry,
    
    -- Enhanced scoring
    (e.phi * e.rho * COALESCE((e.telemetry->>'surprise')::float, 0.0)) as calculated_resonance_score,
    
    -- Priority classification
    CASE 
        WHEN e.prioritization_score > 0.8 THEN 'high_priority'
        WHEN e.prioritization_score > 0.5 THEN 'medium_priority'
        WHEN e.prioritization_score > 0.2 THEN 'low_priority'
        ELSE 'very_low_priority'
    END as priority_level,
    
    -- Family balance
    ROW_NUMBER() OVER (PARTITION BY e.motif_family ORDER BY e.prioritization_score DESC) as family_rank
    
FROM AD_strands e
WHERE e.kind = 'experiment_candidate'
    AND e.created_at >= NOW() - INTERVAL '24 hours'
ORDER BY e.prioritization_score DESC, cap_rank;

-- View for resonance system health (using AD_strands)
CREATE OR REPLACE VIEW v_resonance_system_health AS
SELECT 
    -- Global resonance state (from resonance_state strand)
    rs.module_intelligence->>'theta' as global_theta,
    rs.updated_at as theta_updated_at,
    rs.module_intelligence->>'window' as window,
    rs.module_intelligence->>'delta' as delta,
    rs.module_intelligence->>'alpha' as alpha,
    rs.module_intelligence->>'gamma' as gamma,
    rs.module_intelligence->>'rho_min' as rho_min,
    rs.module_intelligence->>'rho_max' as rho_max,
    
    -- System metrics
    (SELECT COUNT(*) FROM AD_strands WHERE kind = 'motif' AND phi > 0.1) as active_motifs,
    (SELECT COUNT(*) FROM AD_strands WHERE kind = 'motif' AND phi > 0.8) as high_resonance_motifs,
    (SELECT COUNT(*) FROM AD_strands WHERE kind = 'experiment_candidate') as queued_experiments,
    (SELECT COUNT(*) FROM AD_strands WHERE kind = 'resonance_event' AND created_at > NOW() - INTERVAL '1 hour') as recent_events,
    
    -- Performance metrics
    (SELECT AVG(phi) FROM AD_strands WHERE kind = 'motif' AND phi > 0.1) as avg_phi,
    (SELECT AVG(rho) FROM AD_strands WHERE kind = 'motif' AND rho > 0.1) as avg_rho,
    (SELECT AVG(phi * rho) FROM AD_strands WHERE kind = 'motif' AND phi > 0.1) as avg_field_strength,
    
    -- Health indicators
    CASE 
        WHEN (rs.module_intelligence->>'theta')::float > 0.5 AND (SELECT COUNT(*) FROM AD_strands WHERE kind = 'motif' AND phi > 0.1) > 10 THEN 'healthy'
        WHEN (rs.module_intelligence->>'theta')::float > 0.2 AND (SELECT COUNT(*) FROM AD_strands WHERE kind = 'motif' AND phi > 0.1) > 5 THEN 'degraded'
        ELSE 'unhealthy'
    END as system_health,
    
    -- Last update times
    (SELECT MAX(phi_updated_at) FROM AD_strands WHERE kind = 'motif') as last_phi_update,
    (SELECT MAX(rho_updated_at) FROM AD_strands WHERE kind = 'motif') as last_rho_update,
    (SELECT MAX(created_at) FROM AD_strands WHERE kind = 'experiment_candidate') as last_queue_update
    
FROM AD_strands rs
WHERE rs.kind = 'resonance_state'
ORDER BY rs.updated_at DESC
LIMIT 1;

-- View for resonance learning progress
CREATE OR REPLACE VIEW v_resonance_learning_progress AS
SELECT 
    DATE_TRUNC('hour', created_at) as hour_bucket,
    motif_family,
    
    -- Learning metrics
    COUNT(*) as motif_occurrences,
    AVG(phi) as avg_phi,
    AVG(rho) as avg_rho,
    AVG(phi * rho) as avg_field_strength,
    
    -- Performance metrics
    AVG(COALESCE((telemetry->>'sr')::float, 0.0)) as avg_success_rate,
    AVG(COALESCE((telemetry->>'cr')::float, 0.0)) as avg_confirmation_rate,
    AVG(COALESCE((telemetry->>'xr')::float, 0.0)) as avg_contradiction_rate,
    AVG(COALESCE((telemetry->>'surprise')::float, 0.0)) as avg_surprise,
    
    -- Learning indicators
    CASE 
        WHEN AVG(phi) > LAG(AVG(phi)) OVER (PARTITION BY motif_family ORDER BY DATE_TRUNC('hour', created_at)) THEN 'improving'
        WHEN AVG(phi) < LAG(AVG(phi)) OVER (PARTITION BY motif_family ORDER BY DATE_TRUNC('hour', created_at)) THEN 'declining'
        ELSE 'stable'
    END as learning_trend,
    
    -- Resonance quality
    COUNT(CASE WHEN phi > 0.8 AND rho > 1.2 THEN 1 END) as high_resonance_count,
    COUNT(CASE WHEN phi > 0.5 AND rho > 1.0 THEN 1 END) as medium_resonance_count,
    COUNT(CASE WHEN phi > 0.2 AND rho > 0.8 THEN 1 END) as low_resonance_count
    
FROM AD_strands
WHERE kind = 'motif'
    AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', created_at), motif_family
ORDER BY hour_bucket DESC, avg_field_strength DESC;

-- Function to get resonance-enhanced score for a specific strand
CREATE OR REPLACE FUNCTION get_resonance_enhanced_score(p_strand_id TEXT)
RETURNS TABLE(
    strand_id TEXT,
    current_score FLOAT,
    resonance_score FLOAT,
    final_score FLOAT,
    resonance_quality TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id::TEXT,
        (s.sig_sigma * 0.4 + s.sig_confidence * 0.3 + s.accumulated_score * 0.3)::FLOAT as current_score,
        (s.phi * s.rho * COALESCE((s.telemetry->>'surprise')::float, 0.0))::FLOAT as resonance_score,
        ((s.sig_sigma * 0.4 + s.sig_confidence * 0.3 + s.accumulated_score * 0.3) * 
         (1 + (s.phi * s.rho * COALESCE((s.telemetry->>'surprise')::float, 0.0)) * 0.2))::FLOAT as final_score,
        CASE 
            WHEN s.phi > 0.8 AND s.rho > 1.2 THEN 'high_resonance'
            WHEN s.phi > 0.5 AND s.rho > 1.0 THEN 'medium_resonance'
            WHEN s.phi > 0.2 AND s.rho > 0.8 THEN 'low_resonance'
            ELSE 'no_resonance'
        END::TEXT as resonance_quality
    FROM AD_strands s
    WHERE s.id = p_strand_id;
END;
$$ LANGUAGE plpgsql;

-- Function to update resonance state for a motif
CREATE OR REPLACE FUNCTION update_motif_resonance(
    p_motif_id TEXT,
    p_phi FLOAT,
    p_rho FLOAT
) RETURNS VOID AS $$
BEGIN
    UPDATE AD_strands 
    SET 
        phi = p_phi,
        rho = p_rho,
        phi_updated_at = NOW(),
        rho_updated_at = NOW()
    WHERE id = p_motif_id;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate resonance score for experiment prioritization
CREATE OR REPLACE FUNCTION calculate_experiment_resonance_score(
    p_hypothesis_id TEXT
) RETURNS FLOAT AS $$
DECLARE
    v_phi FLOAT;
    v_rho FLOAT;
    v_surprise FLOAT;
    v_resonance_score FLOAT;
BEGIN
    -- Get motif resonance values
    SELECT m.phi, m.rho, COALESCE((m.telemetry->>'surprise')::float, 0.0)
    INTO v_phi, v_rho, v_surprise
    FROM AD_strands h
    LEFT JOIN AD_strands m ON h.hypothesis_id = m.motif_id
    WHERE h.id = p_hypothesis_id;
    
    -- Calculate resonance score: φ · ρ · surprise
    v_resonance_score := COALESCE(v_phi, 0.0) * COALESCE(v_rho, 1.0) * COALESCE(v_surprise, 0.0);
    
    RETURN v_resonance_score;
END;
$$ LANGUAGE plpgsql;
