"""
Tipagens de saída das ferramentas MCP.

Usamos TypedDict para manter respostas previsíveis, padronizadas e fortemente tipadas
para clientes e serviços analíticos, evitando ambiguidade de campos.
"""

from __future__ import annotations

from typing import Optional

try:  # Pydantic <3 exige typing_extensions.TypedDict em Python < 3.12
    from typing_extensions import TypedDict  # type: ignore
except ImportError:  # pragma: no cover - fallback para ambientes que já suportam
    from typing import TypedDict  # type: ignore


class PatientCaptureResult(TypedDict):
    paciente_id: int
    name: str  # iniciais (ver domain.patient.to_initials)
    age: Optional[str]  # idade textual (ver domain.patient.compute_age_display)
    sex: Optional[str]


class ConditionResult(TypedDict):
    paciente_id: int
    paciente_initials: str
    age: Optional[str]  # idade textual; a data de nascimento nunca é exposta
    sex: Optional[str]
    condition_id: int
    cid_code: Optional[str]
    cid_description: Optional[str]
    ciap_code: Optional[str]
    ciap_description: Optional[str]
    dt_inicio_condicao: Optional[str]
    dt_fim_condicao: Optional[str]
    situacao_id: Optional[str]
    observacao: Optional[str]


class CountResult(TypedDict):
    count: int


# `tools/gestantes.py` está registrada em STANDALONE_TOOLS e é coberta pela
# suíte de privacidade via tests/casos_tools.py. A tool já anonimiza
# corretamente (to_initials + sem data de nascimento na saída).
class GestanteResult(TypedDict):
    gestacao_id: int
    paciente_id: int
    paciente_initials: str
    dpp: Optional[str]
    idade_gestacional_semanas: Optional[int]
    idade_gestacional_dias: Optional[int]
    idade_gestacional_str: Optional[str]
    tp_gravidez: Optional[str]
    st_alto_risco: Optional[str]
    situacao: Optional[str]


class HealthConditionCode(TypedDict):
    code: str
    description: Optional[str]


class HealthConditionCaptureResult(TypedDict):
    condition: str
    source: str
    cid_codes: list[str]
    ciap_codes: list[str]
    cid: list[HealthConditionCode]
    ciap: list[HealthConditionCode]
    fallback_condition_text: Optional[str]


class HealthUnitResult(TypedDict):
    unidade_id: int
    cnes: Optional[str]
    name: Optional[str]
    localidade_id: Optional[int]
    is_active: bool
    tipo_cnes: Optional[int]
    tipo_unidade: Optional[str]


class AtendimentoSOAPResult(TypedDict):
    atendimento_id: int
    paciente_id: int
    data_hora: Optional[str]
    cbo_codigo: Optional[str]
    cbo_descricao: Optional[str]
    profissional: Optional[str]
    tipo_profissional_id: Optional[str]
    tipo_atendimento_id: Optional[str]
    soap_s: Optional[str]
    soap_o: Optional[str]
    soap_a: Optional[str]
    soap_p: Optional[str]
    condicoes: Optional[list["SOAPCondition"]]


class SOAPCondition(TypedDict, total=False):
    condition_id: Optional[int]
    cid_code: Optional[str]
    cid_description: Optional[str]
    ciap_code: Optional[str]
    ciap_description: Optional[str]
    observacao: Optional[str]
    dt_inicio_condicao: Optional[str]
    dt_fim_condicao: Optional[str]
    situacao_id: Optional[str]


class AntropometriaResult(TypedDict):
    paciente_id: int
    peso_kg: Optional[float]
    altura_cm: Optional[float]
    imc: Optional[float]
    data_medicao: Optional[str]
    profissional_id: Optional[int]
    profissional_nome: Optional[str]
    tipo_profissional: Optional[str]  # "médico", "enfermeiro", "ACS", etc.
    origem: str  # "pec" ou "visita_domiciliar"


class PAResult(TypedDict):
    paciente_id: int
    pas: Optional[int]
    pad: Optional[int]
    pressao_raw: Optional[str]
    data_medicao: Optional[str]
    profissional_id: Optional[int]
    profissional_nome: Optional[str]
    tipo_profissional: Optional[str]
    origem: str


class HGTResult(TypedDict):
    paciente_id: int
    valor_mg_dl: Optional[float]
    momento_afericao: Optional[str]
    data_medicao: Optional[str]
    profissional_id: Optional[int]
    profissional_nome: Optional[str]
    tipo_profissional: Optional[str]
    origem: str


class HbA1cResult(TypedDict):
    paciente_id: int
    valor_percentual: Optional[float]
    data_realizacao: Optional[str]
    data_resultado: Optional[str]


class MedicationPrescriptionResult(TypedDict):
    paciente_id: int
    prescricao_id: int
    atendimento_id: int
    data_prescricao: Optional[str]
    medicamento: Optional[str]
    concentracao: Optional[str]
    unidade_fornecimento: Optional[str]
    dose: Optional[str]
    unidade_dose_id: Optional[int]
    dose_manha: Optional[str]
    dose_tarde: Optional[str]
    dose_noite: Optional[str]
    frequencia_tipo: Optional[int]
    frequencia_descricao: Optional[str]
    frequencia_periodo: Optional[str]
    frequencia_unidade_tempo: Optional[int]
    posologia: Optional[str]
    via_administracao_id: Optional[int]
    quantidade_receitada: Optional[str]
    inicio_tratamento: Optional[str]
    fim_tratamento: Optional[str]
    duracao_tratamento: Optional[str]
    duracao_unidade_tempo: Optional[int]
    uso_continuo: bool
    dose_unica: bool
    recomendacao: Optional[str]
    interrompido: bool
    data_interrupcao: Optional[str]
    motivo_interrupcao: Optional[str]
    grupo_renovacao_id: Optional[int]
    cid_code: Optional[str]
    ciap_code: Optional[str]
    estado: str
    alerta_consistencia_documental: bool


class VisitaACSResult(TypedDict):
    visita_id: int
    profissional: Optional[str]
    data_visita: Optional[str]
    paciente_id: Optional[int]
    paciente_nome: Optional[str]
    turno: Optional[str]
    desfecho: Optional[str]
    motivo_visita: Optional[list]
    acompanhamentos: Optional[list]
    tem_peso_altura: bool
    tem_pa: bool
    tem_glicemia: bool


class VisitaACSCountResult(TypedDict):
    count: int


class PacienteSemConsultaResult(TypedDict):
    paciente_id: int
    paciente_initials: str
    age: Optional[str]
    sex: Optional[str]
    ultima_consulta: Optional[str]
    dias_sem_consulta: Optional[int]


class VacinaResult(TypedDict):
    paciente_id: int
    imunobiologico: Optional[str]
    sigla: Optional[str]
    dose: Optional[str]
    data_aplicacao: Optional[str]
    lote: Optional[str]
    origem_registro: str
    registro_valido: bool


class ProcedimentoResult(TypedDict):
    paciente_id: int
    codigo_sigtap: Optional[str]
    nome_procedimento: Optional[str]
    data_realizacao: Optional[str]
    quantidade: Optional[int]
    profissional_nome: Optional[str]
    cbo_descricao: Optional[str]
    contexto: str


# ──────────────────────────────────────────────────────────────
# M3: Saúde Bucal (eSB / Indicadores B1-B6)
# ──────────────────────────────────────────────────────────────


class AtendimentoOdontoResult(TypedDict):
    atendimento_id: int
    paciente_id: int
    paciente_initials: str
    data_hora: Optional[str]
    profissional_nome: Optional[str]
    cbo_codigo: Optional[str]
    cbo_descricao: Optional[str]
    unidade_cnes: Optional[str]
    unidade_nome: Optional[str]
    equipe_ine: Optional[str]
    tipo_consulta: Optional[str]
    tipo_atendimento: Optional[str]
    st_gestante: bool
    st_tratamento_concluido: bool
    fornecimento_escova: bool
    fornecimento_creme: bool
    fornecimento_fio: bool
    vigilancia_abscesso: bool
    vigilancia_dor_dente: bool


class ProcedimentoOdontoResult(TypedDict):
    paciente_id: int
    atendimento_id: Optional[int]
    codigo_sigtap: Optional[str]
    nome_procedimento: Optional[str]
    quantidade: int
    data_realizacao: Optional[str]
    profissional_nome: Optional[str]
    cbo_codigo: Optional[str]
    cbo_descricao: Optional[str]
    is_exodontia: bool
    is_preventivo: bool
    is_tra_art: bool


class ProblemaOdontoResult(TypedDict):
    paciente_id: int
    paciente_initials: str
    atendimento_id: Optional[int]
    cid_code: Optional[str]
    cid_description: Optional[str]
    ciap_code: Optional[str]
    ciap_description: Optional[str]
    situacao: Optional[str]
    data_inicio: Optional[str]
    profissional_nome: Optional[str]
    cbo_codigo: Optional[str]


# ──────────────────────────────────────────────────────────────
# M4: Atividades Coletivas & eMulti (Indicadores M1-M2)
# ──────────────────────────────────────────────────────────────


class AtividadeColetivaResult(TypedDict):
    atividade_id: int
    data_atividade: Optional[str]
    unidade_cnes: Optional[str]
    unidade_nome: Optional[str]
    equipe_ine: Optional[str]
    equipe_nome: Optional[str]
    responsavel_nome: Optional[str]
    cbo_codigo: Optional[str]
    cbo_descricao: Optional[str]
    tipo_atividade: Optional[str]
    num_participantes: int
    num_avaliacoes_alteradas: int
    temas_reuniao: list[str]
    temas_saude: list[str]
    praticas_saude: list[str]
    is_pse: bool
    is_pts: bool


class ParticipacaoColetivaResult(TypedDict):
    atividade_id: int
    paciente_id: Optional[int]
    paciente_initials: str
    data_atividade: Optional[str]
    tipo_atividade: Optional[str]
    peso_kg: Optional[float]
    altura_cm: Optional[float]
    st_avaliacao_alterada: bool
    st_cessou_habito_fumar: bool
    st_abandonou_grupo: bool


class ProfissionalAtividadeColetivaResult(TypedDict):
    atividade_id: int
    profissional_id: Optional[int]
    profissional_nome: Optional[str]
    cbo_codigo: Optional[str]
    cbo_descricao: Optional[str]
    is_emulti: bool
    equipe_ine: Optional[str]


# ──────────────────────────────────────────────────────────────
# M5: Programa Saúde na Escola (PSE)
# ──────────────────────────────────────────────────────────────


class AcaoPSEResult(TypedDict):
    atividade_id: int
    inep_escola: Optional[str]
    nome_escola: Optional[str]
    data_atividade: Optional[str]
    equipe_ine: Optional[str]
    equipe_nome: Optional[str]
    responsavel_nome: Optional[str]
    cbo_codigo: Optional[str]
    num_participantes: int
    verificacao_vacinal: bool
    avaliacao_antropometrica: bool
    saude_bucal_escovacao: bool
    saude_bucal_fluor: bool
    saude_ocular: bool
    saude_auditiva: bool


__all__ = [
    "PatientCaptureResult",
    "ConditionResult",
    "CountResult",
    "GestanteResult",
    "HealthConditionCode",
    "HealthConditionCaptureResult",
    "HealthUnitResult",
    "AtendimentoSOAPResult",
    "SOAPCondition",
    "AntropometriaResult",
    "PAResult",
    "HGTResult",
    "HbA1cResult",
    "MedicationPrescriptionResult",
    "VisitaACSResult",
    "VisitaACSCountResult",
    "PacienteSemConsultaResult",
    "VacinaResult",
    "ProcedimentoResult",
    "AtendimentoOdontoResult",
    "ProcedimentoOdontoResult",
    "ProblemaOdontoResult",
    "AtividadeColetivaResult",
    "ParticipacaoColetivaResult",
    "ProfissionalAtividadeColetivaResult",
    "AcaoPSEResult",
]
