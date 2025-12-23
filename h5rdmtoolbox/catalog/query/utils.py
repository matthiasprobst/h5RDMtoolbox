import json
from datetime import datetime, date, time
from decimal import Decimal

import pandas as pd
from rdflib import Graph

# --- minimal caster for common XSD datatypes ---
_XSD = "http://www.w3.org/2001/XMLSchema#"
_NUM_DT = {
    _XSD + "integer", _XSD + "int", _XSD + "long", _XSD + "short",
    _XSD + "byte", _XSD + "nonNegativeInteger", _XSD + "nonPositiveInteger",
    _XSD + "positiveInteger", _XSD + "negativeInteger"
}
_FLOAT_DT = {_XSD + "float", _XSD + "double"}
_DEC_DT = {_XSD + "decimal"}


def sparql_query_to_jsonld(graph: Graph, query: str) -> dict:
    results = graph.query(query)

    jsonld = {
        "@context": {},
        "@graph": []
    }

    for row in results:
        item = {}
        for var, value in row.asdict().items():
            if value is not None:
                if hasattr(value, 'n3'):
                    val_str = value.n3(graph.namespace_manager)
                else:
                    val_str = str(value)

                item[var] = val_str

                # Add simple context mapping
                if isinstance(value, (str, int, float)):
                    jsonld["@context"][var] = None
                elif value.__class__.__name__ == 'URIRef':
                    jsonld["@context"][var] = str(value)

        if item:
            jsonld["@graph"].append(item)

    return jsonld


def _cast_cell(cell, cast_literals: bool):
    """cell is a SPARQL JSON binding object like {'type': 'literal', 'value': '42', 'datatype': '...'}"""
    if cell is None:
        return None
    t = cell.get("type")
    v = cell.get("value")
    if not cast_literals:
        return v
    if t == "literal":
        dt = cell.get("datatype")
        if dt in _NUM_DT:
            try:
                return int(v)
            except Exception:
                return v
        if dt in _FLOAT_DT:
            try:
                return float(v)
            except Exception:
                return v
        if dt in _DEC_DT:
            try:
                return Decimal(v)
            except Exception:
                return v
        if dt == _XSD + "boolean":
            return v.lower() == "true"
        if dt == _XSD + "dateTime":
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except Exception:
                return v
        if dt == _XSD + "date":
            try:
                return date.fromisoformat(v)
            except Exception:
                return v
        if dt == _XSD + "time":
            try:
                return time.fromisoformat(v)
            except Exception:
                return v
        # language-tagged literal like {"xml:lang": "en"}
        # fall through to string value
        return v
    # URIs / bnodes: just return string
    return v


def sparql_json_to_dataframe(results_json: dict, cast_literals: bool = True) -> pd.DataFrame:
    """
    Turn a SPARQL SELECT JSON result into a pandas DataFrame.
    Columns are exactly results['head']['vars'] and missing bindings become None.
    """
    vars_ = results_json.get("head", {}).get("vars", [])
    rows = []
    for b in results_json.get("results", {}).get("bindings", []):
        row = {var: _cast_cell(b.get(var), cast_literals) for var in vars_}
        rows.append(row)
    return pd.DataFrame(rows, columns=vars_)


if __name__ == "__main__":
    # Example usage
    g = Graph()
    g.parse(data="""
    @prefix ex: <http://example.org/> .
    ex:subject1 ex:predicate1 "object1" .
    ex:subject2 ex:predicate2 "object2" .
    """, format="turtle")

    query = """
    SELECT ?s ?p ?o WHERE {
        ?s ?p ?o .
    }
    """
    jsonld_result = sparql_query_to_jsonld(g, query)
    print(json.dumps(jsonld_result, indent=2))

    query2 = """
    PREFIX ex: <http://example.org/>
    SELECT ?p ?o WHERE {
        ex:subject1 ?p ?o .
    }
    """
    jsonld_result = sparql_query_to_jsonld(g, query2)
    print(json.dumps(jsonld_result, indent=2))
