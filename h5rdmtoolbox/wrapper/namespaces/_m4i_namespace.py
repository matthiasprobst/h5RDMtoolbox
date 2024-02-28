from rdflib.namespace import DefinedNamespace, Namespace
from rdflib.term import URIRef


class LanguageExtension:
    pass

class M4I(DefinedNamespace):
    # uri = "https://w3id.org/nfdi4ing/metadata4ing#"
    # Generated with h5rdmtoolbox.data.m4i.generate_namespace_file()
    # Date: 2024-02-28 07:59:08.869430
    Method: URIRef  # ['Methode', 'method']
    NumericalAssignment: URIRef  # ['numerical assignment', 'numerische Zuweisung']
    NumericalVariable: URIRef  # ['numerical variable', 'numerische Variable']
    ProcessingStep: URIRef  # ['Arbeitsschritt', 'processing step']
    TextVariable: URIRef  # ['text variable', 'textbasierte Variable']
    Tool: URIRef  # ['Werkzeug', 'tool']
    UncertaintyDeclaration: URIRef  # ['Unsicherheitsdeklaration', 'uncertainty declaration']
    hasAdmissibleUnit: URIRef  # ['has admissible unit', 'hat als zulässige Einheit']
    hasAdmissibleValue: URIRef  # ['has admissible value', 'hat als zulässigen Wert']
    hasAssignedValue: URIRef  # ['has assigned value', 'hat zugewiesenen Wert']
    hasCoverageInterval: URIRef  # ['has coverage interval', 'hat Überdeckungsintervall']
    hasEmployedTool: URIRef  # ['has employed tool', 'hat eingesetztes Werkzeug']
    hasExpandedUnc: URIRef  # ['has expanded uncertainty', 'hat erweiterte Unsicherheit']
    hasKindOfQuantity: URIRef  # ['has kind of quantity', 'hat Größenart']
    hasParameter: URIRef  # ['has parameter', 'hat Parameter']
    hasRuntimeAssignment: URIRef  # ['has runtime assignment', 'hat Laufzeitzuweisung']
    hasUncertaintyDeclaration: URIRef  # ['has uncertainty declaration', 'hat Unsicherheitsdeklaration']
    hasUnit: URIRef  # ['has unit', 'hat Einheit']
    hasVariable: URIRef  # ['has variable', 'hat Variable']
    inProject: URIRef  # ['associated to project', 'gehört zu Projekt']
    investigates: URIRef  # ['investigates', 'untersucht']
    investigatesProperty: URIRef  # ['investigates property', 'untersucht Eigenschaft']
    isEmployedToolIn: URIRef  # ['is employed tool', 'ist eingesetztes Werkzeug']
    projectParticipant: URIRef  # ['hat Projektmitglied', 'project participant']
    realizesMethod: URIRef  # ['realisiert Methode', 'realizes method']
    UsageInstruction: URIRef  # ['Verwendungshinweis', 'usage instruction']
    endOfProject: URIRef  # ['Projektenddatum', 'project end date']
    hasAssignmentTimestamp: URIRef  # ['has assignment timestamp', 'hat Zuweisungszeitstempel']
    hasDateAssignmentCreated: URIRef  # ['has date assignment created', 'hat Datumszuweisung erzeugt']
    hasDateAssignmentDeleted: URIRef  # ['has date assignment deleted', 'hat Datumszuweisung gelöscht']
    hasDateAssignmentModified: URIRef  # ['has date assignment modified', 'hat Datumszuweisung bearbeitet']
    hasDateAssignmentValidFrom: URIRef  # ['has date assignment valid from', 'hat Datumszuweisung gültig ab']
    hasDateAssignmentValidUntil: URIRef  # ['has date assignment valid until', 'hat Datumszuweisung gültig bis']
    hasMaximumValue: URIRef  # ['has maximum value', 'hat Maximalwert']
    hasMinimumValue: URIRef  # ['has minimum value', 'hat Minimalwert']
    hasNumericalValue: URIRef  # ['has numerical value', 'hat Zahlenwert']
    hasRorId: URIRef  # ['has ROR ID', 'hat ROR ID']
    hasStepSize: URIRef  # ['has step size', 'hat Schrittweite']
    hasStringValue: URIRef  # ['has string value', 'hat Zeichenwert']
    hasSymbol: URIRef  # ['has symbol', 'hat Symbol']
    hasValue: URIRef  # ['has value', 'hat Wert']
    hasVariableDescription: URIRef  # ['has variable description', 'hat Variablenbeschreibung']
    identifier: URIRef  # ['has identifier', 'hat Identifikator']
    orcidId: URIRef  # ['has ORCID ID', 'hat ORCID ID']
    projectReferenceID: URIRef  # ['has project ID', 'hat Projekt-ID']
    startOfProject: URIRef  # ['Projektstartdatum', 'project start date']
    ContactPerson: URIRef  # ['Kontaktperson', 'contact person']
    DataCollector: URIRef  # ['Datenerfasser*in', 'data collector']
    DataCurator: URIRef  # ['Datenkurator*in', 'data curator']
    DataManager: URIRef  # ['Datenverwalter*in', 'data manager']
    Distributor: URIRef  # ['Anbieter*in', 'distributor']
    Editor: URIRef  # ['Herausgeber*in', 'editor']
    HostingInstitution: URIRef  # ['bereitstellende Institution', 'hosting institution']
    Other: URIRef  # ['other person', 'weitere Person']
    Producer: URIRef  # ['Produzent*in', 'producer']
    ProjectLeader: URIRef  # ['Projektleiter*in', 'project leader']
    ProjectManager: URIRef  # ['Projektmanager*in', 'project manager']
    ProjectMember: URIRef  # ['Projektmitglied', 'project member']
    RegistrationAgency: URIRef  # ['Registrierungsstelle', 'registration agency']
    RegistrationAuthority: URIRef  # ['Registrierungsbehörde', 'registration authority']
    RelatedPerson: URIRef  # ['related person', 'zugehörige Person']
    ResearchGroup: URIRef  # ['Forschungsgruppe', 'research group']
    Researcher: URIRef  # ['Rechercheur*in', 'researcher']
    RightsHolder: URIRef  # ['Rechteinhaber*in', 'rights holder']
    Sponsor: URIRef  # ['Sponsor*in', 'sponsor']
    Supervisor: URIRef  # ['Betreuer*in', 'supervisor']
    WorkPackageLeader: URIRef  # ['Arbeitspaketleiter*in', 'work package leader']

    _NS = Namespace("http://w3id.org/nfdi4ing/metadata4ing#")

de = LanguageExtension()

setattr(de, "Methode", M4I.Method)
setattr(M4I, "method", M4I.Method)
setattr(M4I, "numerical_assignment", M4I.NumericalAssignment)
setattr(M4I, "numerische_Zuweisung", M4I.NumericalAssignment)
setattr(M4I, "numerical_variable", M4I.NumericalVariable)
setattr(de, "numerische_Variable", M4I.NumericalVariable)
setattr(de, "Arbeitsschritt", M4I.ProcessingStep)
setattr(M4I, "processing_step", M4I.ProcessingStep)
setattr(M4I, "text_variable", M4I.TextVariable)
setattr(de, "textbasierte_Variable", M4I.TextVariable)
setattr(de, "Werkzeug", M4I.Tool)
setattr(M4I, "tool", M4I.Tool)
setattr(de, "Unsicherheitsdeklaration", M4I.UncertaintyDeclaration)
setattr(M4I, "uncertainty_declaration", M4I.UncertaintyDeclaration)
setattr(M4I, "has_admissible_unit", M4I.hasAdmissibleUnit)
setattr(de, "hat_als_zulässige_Einheit", M4I.hasAdmissibleUnit)
setattr(M4I, "has_admissible_value", M4I.hasAdmissibleValue)
setattr(de, "hat_als_zulässigen_Wert", M4I.hasAdmissibleValue)
setattr(M4I, "has_assigned_value", M4I.hasAssignedValue)
setattr(de, "hat_zugewiesenen_Wert", M4I.hasAssignedValue)
setattr(M4I, "has_coverage_interval", M4I.hasCoverageInterval)
setattr(M4I, "hat_Überdeckungsintervall", M4I.hasCoverageInterval)
setattr(M4I, "has_employed_tool", M4I.hasEmployedTool)
setattr(de, "hat_eingesetztes_Werkzeug", M4I.hasEmployedTool)
setattr(M4I, "has_expanded_uncertainty", M4I.hasExpandedUnc)
setattr(de, "hat_erweiterte_Unsicherheit", M4I.hasExpandedUnc)
setattr(M4I, "has_kind_of_quantity", M4I.hasKindOfQuantity)
setattr(de, "hat_Größenart", M4I.hasKindOfQuantity)
setattr(M4I, "has_parameter", M4I.hasParameter)
setattr(de, "hat_Parameter", M4I.hasParameter)
setattr(M4I, "has_runtime_assignment", M4I.hasRuntimeAssignment)
setattr(de, "hat_Laufzeitzuweisung", M4I.hasRuntimeAssignment)
setattr(M4I, "has_uncertainty_declaration", M4I.hasUncertaintyDeclaration)
setattr(de, "hat_Unsicherheitsdeklaration", M4I.hasUncertaintyDeclaration)
setattr(M4I, "has_unit", M4I.hasUnit)
setattr(de, "hat_Einheit", M4I.hasUnit)
setattr(M4I, "has_variable", M4I.hasVariable)
setattr(de, "hat_Variable", M4I.hasVariable)
setattr(M4I, "associated_to_project", M4I.inProject)
setattr(de, "gehört_zu_Projekt", M4I.inProject)
setattr(M4I, "investigates", M4I.investigates)
setattr(de, "untersucht", M4I.investigates)
setattr(M4I, "investigates_property", M4I.investigatesProperty)
setattr(de, "untersucht_Eigenschaft", M4I.investigatesProperty)
setattr(M4I, "is_employed_tool", M4I.isEmployedToolIn)
setattr(de, "ist_eingesetztes_Werkzeug", M4I.isEmployedToolIn)
setattr(de, "hat_Projektmitglied", M4I.projectParticipant)
setattr(M4I, "project_participant", M4I.projectParticipant)
setattr(de, "realisiert_Methode", M4I.realizesMethod)
setattr(M4I, "realizes_method", M4I.realizesMethod)
setattr(de, "Verwendungshinweis", M4I.UsageInstruction)
setattr(M4I, "usage_instruction", M4I.UsageInstruction)
setattr(de, "Projektenddatum", M4I.endOfProject)
setattr(M4I, "project_end_date", M4I.endOfProject)
setattr(M4I, "has_assignment_timestamp", M4I.hasAssignmentTimestamp)
setattr(de, "hat_Zuweisungszeitstempel", M4I.hasAssignmentTimestamp)
setattr(M4I, "has_date_assignment_created", M4I.hasDateAssignmentCreated)
setattr(de, "hat_Datumszuweisung_erzeugt", M4I.hasDateAssignmentCreated)
setattr(M4I, "has_date_assignment_deleted", M4I.hasDateAssignmentDeleted)
setattr(de, "hat_Datumszuweisung_gelöscht", M4I.hasDateAssignmentDeleted)
setattr(M4I, "has_date_assignment_modified", M4I.hasDateAssignmentModified)
setattr(de, "hat_Datumszuweisung_bearbeitet", M4I.hasDateAssignmentModified)
setattr(M4I, "has_date_assignment_valid_from", M4I.hasDateAssignmentValidFrom)
setattr(de, "hat_Datumszuweisung_gültig_ab", M4I.hasDateAssignmentValidFrom)
setattr(M4I, "has_date_assignment_valid_until", M4I.hasDateAssignmentValidUntil)
setattr(de, "hat_Datumszuweisung_gültig_bis", M4I.hasDateAssignmentValidUntil)
setattr(M4I, "has_maximum_value", M4I.hasMaximumValue)
setattr(de, "hat_Maximalwert", M4I.hasMaximumValue)
setattr(M4I, "has_minimum_value", M4I.hasMinimumValue)
setattr(de, "hat_Minimalwert", M4I.hasMinimumValue)
setattr(M4I, "has_numerical_value", M4I.hasNumericalValue)
setattr(de, "hat_Zahlenwert", M4I.hasNumericalValue)
setattr(M4I, "has_ROR_ID", M4I.hasRorId)
setattr(M4I, "hat_ROR_ID", M4I.hasRorId)
setattr(M4I, "has_step_size", M4I.hasStepSize)
setattr(de, "hat_Schrittweite", M4I.hasStepSize)
setattr(M4I, "has_string_value", M4I.hasStringValue)
setattr(de, "hat_Zeichenwert", M4I.hasStringValue)
setattr(M4I, "has_symbol", M4I.hasSymbol)
setattr(de, "hat_Symbol", M4I.hasSymbol)
setattr(M4I, "has_value", M4I.hasValue)
setattr(de, "hat_Wert", M4I.hasValue)
setattr(M4I, "has_variable_description", M4I.hasVariableDescription)
setattr(de, "hat_Variablenbeschreibung", M4I.hasVariableDescription)
setattr(M4I, "has_identifier", M4I.identifier)
setattr(de, "hat_Identifikator", M4I.identifier)
setattr(M4I, "has_ORCID_ID", M4I.orcidId)
setattr(de, "hat_ORCID_ID", M4I.orcidId)
setattr(M4I, "has_project_ID", M4I.projectReferenceID)
setattr(de, "hat_Projekt-ID", M4I.projectReferenceID)
setattr(de, "Projektstartdatum", M4I.startOfProject)
setattr(M4I, "project_start_date", M4I.startOfProject)
setattr(de, "Kontaktperson", M4I.ContactPerson)
setattr(M4I, "contact_person", M4I.ContactPerson)
setattr(de, "Datenerfasser*in", M4I.DataCollector)
setattr(M4I, "data_collector", M4I.DataCollector)
setattr(de, "Datenkurator*in", M4I.DataCurator)
setattr(M4I, "data_curator", M4I.DataCurator)
setattr(de, "Datenverwalter*in", M4I.DataManager)
setattr(M4I, "data_manager", M4I.DataManager)
setattr(de, "Anbieter*in", M4I.Distributor)
setattr(M4I, "distributor", M4I.Distributor)
setattr(de, "Herausgeber*in", M4I.Editor)
setattr(M4I, "editor", M4I.Editor)
setattr(de, "bereitstellende_Institution", M4I.HostingInstitution)
setattr(M4I, "hosting_institution", M4I.HostingInstitution)
setattr(M4I, "other_person", M4I.Other)
setattr(de, "weitere_Person", M4I.Other)
setattr(de, "Produzent*in", M4I.Producer)
setattr(M4I, "producer", M4I.Producer)
setattr(de, "Projektleiter*in", M4I.ProjectLeader)
setattr(M4I, "project_leader", M4I.ProjectLeader)
setattr(de, "Projektmanager*in", M4I.ProjectManager)
setattr(M4I, "project_manager", M4I.ProjectManager)
setattr(de, "Projektmitglied", M4I.ProjectMember)
setattr(M4I, "project_member", M4I.ProjectMember)
setattr(de, "Registrierungsstelle", M4I.RegistrationAgency)
setattr(M4I, "registration_agency", M4I.RegistrationAgency)
setattr(de, "Registrierungsbehörde", M4I.RegistrationAuthority)
setattr(M4I, "registration_authority", M4I.RegistrationAuthority)
setattr(M4I, "related_person", M4I.RelatedPerson)
setattr(de, "zugehörige_Person", M4I.RelatedPerson)
setattr(de, "Forschungsgruppe", M4I.ResearchGroup)
setattr(M4I, "research_group", M4I.ResearchGroup)
setattr(de, "Rechercheur*in", M4I.Researcher)
setattr(M4I, "researcher", M4I.Researcher)
setattr(de, "Rechteinhaber*in", M4I.RightsHolder)
setattr(M4I, "rights_holder", M4I.RightsHolder)
setattr(de, "Sponsor*in", M4I.Sponsor)
setattr(M4I, "sponsor", M4I.Sponsor)
setattr(de, "Betreuer*in", M4I.Supervisor)
setattr(M4I, "supervisor", M4I.Supervisor)
setattr(de, "Arbeitspaketleiter*in", M4I.WorkPackageLeader)
setattr(M4I, "work_package_leader", M4I.WorkPackageLeader)

setattr(M4I, "de", de)