(function () {
  const config = window.h5tbxGraphConfig || {};
  const graphDataElement = document.getElementById("graph-data");
  const graphData = graphDataElement ? JSON.parse(graphDataElement.textContent) : { nodes: [], edges: [], groups: {} };
  const graphDataUrl = config.graphDataUrl;
  const graphForm = document.getElementById("graph-form");
  const container = document.getElementById("network");
  const emptyGraph = document.getElementById("empty-graph");
  const graphStatus = document.getElementById("graph-status");
  const nodeDetails = document.getElementById("node-details");
  const hiddenNodeToggle = document.getElementById("hidden-node-toggle");
  const hiddenNodeList = document.getElementById("hidden-node-list");
  const classList = document.getElementById("class-list");
  const classSearch = document.getElementById("class-search");
  const classEmpty = document.getElementById("class-empty");
  const classClear = document.getElementById("class-clear");
  const labelModeInput = document.getElementById("label-mode");
  const colorByInput = document.getElementById("color-by");
  const colorSchemeInput = document.getElementById("color-scheme");
  const nodeSizeInput = document.getElementById("node-size");
  const edgeWidthInput = document.getElementById("edge-width");
  const backgroundColorInput = document.getElementById("background-color");
  const expansionDirectionInput = document.getElementById("expansion-direction");
  const expansionDepthInput = document.getElementById("expansion-depth");
  const graphViewInput = document.getElementById("graph-view");
  const currentGraphView = (config.graphView || graphViewInput?.value || "2d").toLowerCase();
  let activeGraphView = currentGraphView;
  const allNodes = new Map();
  const allEdges = new Map();
  const allGroups = {};
  const nodeSources = new Map();
  const edgeSources = new Map();
  const hiddenNodeIds = new Set();
  const expandedNodeIds = new Set();
  const loadingNodeIds = new Set();
  const positionCache = new Map();
  const nodeById = allNodes;
  let activeClassId = null;
  let hideNode = () => {};
  let unhideNode = () => {};
  let refreshVisibleGraph = () => {};
  let navigateToNode = async () => {};
  let network = null;
  let nodes = null;
  let edges = null;
  let last3dClick = { id: null, time: 0 };

  const escapeHtml = (value) => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const edgeKey = (edge) => `${edge.from}\u0000${edge.to}\u0000${edge.label}`;

  const setGraphStatus = (message, kind = "") => {
    if (!graphStatus) {
      return;
    }
    graphStatus.textContent = message || "";
    graphStatus.className = "graph-status";
    if (message) {
      graphStatus.classList.add("visible");
    }
    if (kind) {
      graphStatus.classList.add(kind);
    }
  };

  const renderedLabelsEnabled = () => {
    if (labelModeInput.value === "on") {
      return true;
    }
    if (labelModeInput.value === "off") {
      return false;
    }
    return allNodes.size <= 250 && allEdges.size <= 500;
  };

  const selectedColorMode = () => colorByInput?.value || config.colorBy || "class";
  const clampNumber = (value, fallback, minimum, maximum) => {
    const parsed = Number.parseInt(value, 10);
    if (Number.isNaN(parsed)) {
      return fallback;
    }
    return Math.max(minimum, Math.min(maximum, parsed));
  };
  const selectedNodeSize = () => clampNumber(nodeSizeInput?.value || config.nodeSize, 14, 6, 36);
  const selectedEdgeWidth = () => clampNumber(edgeWidthInput?.value || config.edgeWidth, 1, 1, 8);
  const selectedBackgroundColor = () => {
    const color = backgroundColorInput?.value || config.backgroundColor || "#ffffff";
    return /^#[0-9a-fA-F]{6}$/.test(color) ? color : "#ffffff";
  };

  const selectedNodeGroup = (node) => {
    if (selectedColorMode() === "namespace" && node.namespace) {
      return `namespace:${node.namespace}`;
    }
    return node.group || (node.namespace === "blank" ? "blank" : "resource");
  };

  const nodeClassIds = (node) => {
    if (Array.isArray(node.rdf_class_ids)) {
      return node.rdf_class_ids;
    }
    return node.rdf_class ? [`class:${node.rdf_class}`] : [];
  };

  const nodeMatchesActiveClass = (node) => !activeClassId || nodeClassIds(node).includes(activeClassId);
  const edgeTouchesActiveClass = (edge) => {
    if (!activeClassId) {
      return true;
    }
    const fromNode = nodeById.get(edge.from);
    const toNode = nodeById.get(edge.to);
    return Boolean(
      (fromNode && nodeMatchesActiveClass(fromNode))
      || (toNode && nodeMatchesActiveClass(toNode))
    );
  };

  const groupColor = (node) => {
    const group = allGroups[selectedNodeGroup(node)] || {};
    if (typeof group.color === "string") {
      return group.color;
    }
    return group.color?.background || "#0b6f85";
  };

  const visibleNode = (node) => ({
    ...node,
    group: selectedNodeGroup(node),
    label: renderedLabelsEnabled() ? node.label : undefined,
    title: node.label,
    borderWidth: activeClassId && nodeMatchesActiveClass(node) ? 4 : (node.expandable ? 3 : 1),
    size: selectedNodeSize() + (node.expandable ? 3 : 0) + (activeClassId && nodeMatchesActiveClass(node) ? 3 : 0),
    color: activeClassId && !nodeMatchesActiveClass(node)
      ? { background: "#edf1f5", border: "#d8dee6" }
      : undefined,
    font: activeClassId && !nodeMatchesActiveClass(node)
      ? { color: "#98a2b3" }
      : undefined,
    shadow: Boolean(activeClassId && nodeMatchesActiveClass(node))
  });

  const visibleEdge = (edge) => ({
    ...edge,
    id: edgeKey(edge),
    label: renderedLabelsEnabled() ? edge.label : undefined,
    title: edge.label,
    width: activeClassId && edgeTouchesActiveClass(edge) ? selectedEdgeWidth() + 2 : selectedEdgeWidth(),
    color: activeClassId && !edgeTouchesActiveClass(edge)
      ? { color: "#e3e8ef", highlight: "#e3e8ef" }
      : undefined,
    dashes: Boolean(activeClassId && !edgeTouchesActiveClass(edge))
  });

  const applyGraphBackground = () => {
    if (container) {
      container.style.backgroundColor = selectedBackgroundColor();
    }
    if (activeGraphView === "3d" && network && typeof network.backgroundColor === "function") {
      network.backgroundColor(selectedBackgroundColor());
    }
  };

  const rememberPositions = () => {
    if (!network || typeof network.getPositions !== "function") {
      return;
    }
    const positions = network.getPositions();
    Object.entries(positions).forEach(([nodeId, position]) => {
      positionCache.set(nodeId, position);
    });
  };

  const visibleNodeWithPosition = (node) => {
    const renderedNode = visibleNode(node);
    const position = positionCache.get(node.id);
    if (position) {
      renderedNode.x = position.x;
      renderedNode.y = position.y;
    }
    return renderedNode;
  };

  const rememberSource = (sourceMap, id, source) => {
    const sources = sourceMap.get(id) || new Set();
    sources.add(source);
    sourceMap.set(id, sources);
  };

  const forgetSource = (sourceMap, id, source) => {
    const sources = sourceMap.get(id);
    if (!sources) {
      return false;
    }
    sources.delete(source);
    if (sources.size === 0) {
      sourceMap.delete(id);
      return true;
    }
    return false;
  };

  const addGraphPayload = (payload, source) => {
    Object.assign(allGroups, payload.groups || {});
    (payload.nodes || []).forEach((node) => {
      allNodes.set(node.id, { ...(allNodes.get(node.id) || {}), ...node });
      rememberSource(nodeSources, node.id, source);
    });
    (payload.edges || []).forEach((edge) => {
      const key = edgeKey(edge);
      allEdges.set(key, { ...(allEdges.get(key) || {}), ...edge });
      rememberSource(edgeSources, key, source);
    });
  };

  addGraphPayload(graphData, "base");

  const visibleGraphNodes = () => Array.from(allNodes.values()).filter((node) => !hiddenNodeIds.has(node.id));
  const visibleGraphEdges = () => Array.from(allEdges.values())
    .filter((edge) => !hiddenNodeIds.has(edge.from) && !hiddenNodeIds.has(edge.to));

  const classRows = () => {
    const byClass = new Map();
    visibleGraphNodes().forEach((node) => {
      const labels = Array.isArray(node.rdf_classes) ? node.rdf_classes : [];
      nodeClassIds(node).forEach((classId, index) => {
        const row = byClass.get(classId) || {
          id: classId,
          label: labels[index] || classId.replace(/^class:/, ""),
          count: 0,
          color: allGroups[classId]?.color || {}
        };
        row.count += 1;
        byClass.set(classId, row);
      });
    });
    return Array.from(byClass.values()).sort((left, right) => (
      right.count - left.count || left.label.localeCompare(right.label)
    ));
  };

  const renderClassList = () => {
    if (!classList || !classEmpty || !classClear) {
      return;
    }
    const rows = classRows();
    const search = (classSearch?.value || "").trim().toLowerCase();
    const filteredRows = search
      ? rows.filter((row) => row.label.toLowerCase().includes(search) || row.id.toLowerCase().includes(search))
      : rows;
    classClear.classList.toggle("active", activeClassId === null);
    classClear.setAttribute("aria-pressed", String(activeClassId === null));
    classEmpty.textContent = rows.length === 0 ? "No RDF classes are visible." : "No classes match this search.";
    classEmpty.classList.toggle("visible", filteredRows.length === 0);
    classList.innerHTML = filteredRows.map((row) => {
      const color = typeof row.color === "string" ? row.color : (row.color?.background || "#d8dee6");
      const active = row.id === activeClassId;
      return `<button type="button" role="option" aria-selected="${active}" class="${active ? "active" : ""}" data-class-id="${escapeHtml(row.id)}">
        <span class="class-swatch" style="background-color:${escapeHtml(color)}"></span>
        <span class="class-label">${escapeHtml(row.label)}</span>
        <span class="class-count">${row.count}</span>
      </button>`;
    }).join("");
  };

  const activeClassNodeIds = () => visibleGraphNodes()
    .filter(nodeMatchesActiveClass)
    .map((node) => node.id);

  const fitActiveClass = () => {
    if (!activeClassId || !network) {
      return;
    }
    const matchingNodeIds = activeClassNodeIds();
    if (matchingNodeIds.length === 0) {
      return;
    }
    if (activeGraphView === "3d" && typeof network.zoomToFit === "function") {
      const matchingNodeIdSet = new Set(matchingNodeIds);
      network.zoomToFit(500, 80, (node) => matchingNodeIdSet.has(node.id));
      return;
    }
    if (typeof network.fit === "function") {
      network.fit({ nodes: matchingNodeIds, animation: { duration: 450, easingFunction: "easeInOutQuad" } });
    }
  };

  const selectClass = (classId, fit = false) => {
    activeClassId = classId === activeClassId ? null : classId;
    refreshVisibleGraph();
    renderClassList();
    if (fit) {
      fitActiveClass();
    }
  };

  const updateHiddenNodeMenu = () => {
    const hiddenNodes = Array.from(hiddenNodeIds)
      .map((nodeId) => nodeById.get(nodeId))
      .filter(Boolean)
      .sort((left, right) => left.label.localeCompare(right.label));
    hiddenNodeToggle.textContent = `Hidden nodes (${hiddenNodes.length})`;
    hiddenNodeToggle.disabled = hiddenNodes.length === 0;
    if (hiddenNodes.length === 0) {
      hiddenNodeList.innerHTML = "<p>No hidden nodes.</p>";
      hiddenNodeList.classList.remove("open");
      hiddenNodeToggle.setAttribute("aria-expanded", "false");
      return;
    }
    hiddenNodeList.innerHTML = hiddenNodes
      .map((node) => `<button type="button" data-node-id="${escapeHtml(node.id)}">${escapeHtml(node.label)}</button>`)
      .join("");
  };

  if (classList) {
    classList.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-class-id]");
      if (!button) {
        return;
      }
      selectClass(button.dataset.classId, true);
    });
  }

  if (classClear) {
    classClear.addEventListener("click", () => {
      activeClassId = null;
      refreshVisibleGraph();
      renderClassList();
    });
  }

  if (classSearch) {
    classSearch.addEventListener("input", renderClassList);
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && activeClassId) {
      activeClassId = null;
      refreshVisibleGraph();
      renderClassList();
    }
  });

  const showNodeDetails = (node) => {
    const literals = node.literals || [];
    const outgoingLinks = node.outgoing_links || [];
    const incomingLinks = node.incoming_links || [];
    const hiddenNeighborText = node.hidden_neighbor_count
      ? `<p class="no-literals">${node.hidden_neighbor_count} more connected node(s). Double-click to expand.</p>`
      : "";
    const literalRows = literals.length
      ? `<dl>${literals.map((literal) => `<dt>${escapeHtml(literal.predicate)}</dt><dd>${escapeHtml(literal.value)}</dd>`).join("")}</dl>`
      : '<p class="no-literals">No literal values are available for this node.</p>';
    const outgoingRows = outgoingLinks.length
      ? `<section class="outgoing-links-section"><h3>Outgoing connections</h3><dl>${outgoingLinks.map((link) => {
          // prefer the provided label; convert "prefix:Local" -> "prefix.Local"
          const displayLabel = link.target_label
            ? String(link.target_label)
            : String(link.target_id);
          return `<dt>${escapeHtml(link.predicate)}</dt><dd><button type="button" class="outgoing-node-link" data-node-id="${escapeHtml(link.target_id)}" title="${escapeHtml(link.target_id)}">${escapeHtml(displayLabel)}</button></dd>`;
        }).join("")}</dl></section>`
      : "";
    const incomingRows = incomingLinks.length
      ? `<section class="outgoing-links-section"><h3>Incoming connections</h3><dl>${incomingLinks.map((link) => {
          const displayLabel = link.source_label ? String(link.source_label) : String(link.source_id);
          return `<dt>${escapeHtml(link.predicate)}</dt><dd><button type="button" class="outgoing-node-link" data-node-id="${escapeHtml(link.source_id)}" title="${escapeHtml(link.source_id)}">${escapeHtml(displayLabel)}</button></dd>`;
        }).join("")}</dl></section>`
      : "";
    const localLink = node.local_href
      ? `<a class="node-link" href="${escapeHtml(node.local_href)}" target="_blank" rel="noopener">Open local TTL</a>`
      : "";
    nodeDetails.innerHTML = `<div class="node-details-header"><h2>${escapeHtml(node.label)}</h2><button type="button" class="hide-node-button">Hide</button></div>${localLink}${hiddenNeighborText}${literalRows}${outgoingRows}${incomingRows}`;
    nodeDetails.querySelector(".hide-node-button").addEventListener("click", () => {
      hideNode(node.id);
    });
    nodeDetails.style.display = "block";
  };

  nodeDetails.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-node-id].outgoing-node-link, button[data-node-id].incoming-node-link");
    if (!button) {
      return;
    }
    navigateToNode(button.dataset.nodeId);
  });

  hiddenNodeToggle.addEventListener("click", () => {
    const isOpen = hiddenNodeList.classList.toggle("open");
    hiddenNodeToggle.setAttribute("aria-expanded", String(isOpen));
  });

  hiddenNodeList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-node-id]");
    if (!button) {
      return;
    }
    unhideNode(button.dataset.nodeId);
  });

  graphForm.querySelectorAll('input[name="mode"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      if (radio.checked) {
        graphForm.requestSubmit();
      }
    });
  });

  labelModeInput.addEventListener("change", () => {
    refreshVisibleGraph();
  });

  if (colorByInput) {
    colorByInput.addEventListener("change", () => {
      refreshVisibleGraph();
    });
  }

  if (colorSchemeInput) {
    colorSchemeInput.addEventListener("change", () => {
      graphForm.requestSubmit();
    });
  }

  [nodeSizeInput, edgeWidthInput].forEach((input) => {
    if (input) {
      input.addEventListener("input", () => {
        refreshVisibleGraph();
      });
    }
  });

  if (backgroundColorInput) {
    backgroundColorInput.addEventListener("input", () => {
      applyGraphBackground();
    });
  }

  if (graphViewInput) {
    graphViewInput.addEventListener("change", () => {
      graphForm.requestSubmit();
    });
  }

  if (graphData.nodes.length === 0) {
    renderClassList();
    emptyGraph.style.display = "block";
    return;
  }

  if (!window.vis) {
    renderClassList();
    emptyGraph.textContent = "The 2D graph library could not be loaded.";
    emptyGraph.style.display = "block";
    return;
  }

  const groups = allGroups;

  const visible3dNode = (node) => ({
    ...node,
    name: node.label,
    val: (selectedNodeSize() / 14 * 3) + (node.expandable ? 2 : 0) + (activeClassId && nodeMatchesActiveClass(node) ? 2 : 0),
    color: activeClassId && !nodeMatchesActiveClass(node) ? "#d8dee6" : groupColor(node)
  });

  const visible3dLink = (edge) => ({
    ...edge,
    source: edge.from,
    target: edge.to,
    width: activeClassId && edgeTouchesActiveClass(edge) ? selectedEdgeWidth() + 2 : selectedEdgeWidth(),
    color: activeClassId && !edgeTouchesActiveClass(edge) ? "#e3e8ef" : "#9aa4b2"
  });

  const visible3dData = () => ({
    nodes: visibleGraphNodes()
      .map(visible3dNode),
    links: visibleGraphEdges()
      .map(visible3dLink)
  });

  const refresh2dGraph = () => {
    rememberPositions();
    network.setOptions({ groups });
    nodes.clear();
    nodes.add(visibleGraphNodes().map(visibleNodeWithPosition));
    edges.clear();
    edges.add(visibleGraphEdges().map(visibleEdge));
    updateHiddenNodeMenu();
    renderClassList();
  };

  const refresh3dGraph = () => {
    applyGraphBackground();
    network.graphData(visible3dData());
    updateHiddenNodeMenu();
    renderClassList();
  };

  const hasWebGLSupport = () => {
    try {
      const canvas = document.createElement("canvas");
      return Boolean(
        window.WebGLRenderingContext
        && (
          canvas.getContext("webgl2")
          || canvas.getContext("webgl")
          || canvas.getContext("experimental-webgl")
        )
      );
    } catch (error) {
      return false;
    }
  };

  hideNode = (nodeId) => {
    rememberPositions();
    hiddenNodeIds.add(nodeId);
    nodeDetails.style.display = "none";
    if (activeGraphView === "3d") {
      refresh3dGraph();
    } else {
      const incidentEdgeIds = Array.from(allEdges.values())
        .filter((edge) => edge.from === nodeId || edge.to === nodeId)
        .map(edgeKey);
      edges.remove(incidentEdgeIds);
      nodes.remove(nodeId);
      updateHiddenNodeMenu();
      renderClassList();
    }
  };

  unhideNode = (nodeId) => {
    rememberPositions();
    hiddenNodeIds.delete(nodeId);
    if (activeGraphView === "3d") {
      refresh3dGraph();
    } else {
      const node = allNodes.get(nodeId);
      if (node) {
        nodes.update(visibleNodeWithPosition(node));
      }
      const restoredEdges = visibleGraphEdges().map(visibleEdge);
      edges.update(restoredEdges);
      updateHiddenNodeMenu();
      renderClassList();
    }
  };

  const centerNode = (nodeId) => {
    if (!network) {
      return;
    }
    if (typeof network.selectNodes === "function") {
      network.selectNodes([nodeId]);
    }
    if (activeGraphView === "3d" && typeof network.zoomToFit === "function") {
      network.zoomToFit(500, 80, (node) => node.id === nodeId);
      return;
    }
    if (typeof network.focus === "function") {
      network.focus(nodeId, { scale: 1.1, animation: { duration: 450, easingFunction: "easeInOutQuad" } });
    } else if (typeof network.fit === "function") {
      network.fit({ nodes: [nodeId], animation: { duration: 450, easingFunction: "easeInOutQuad" } });
    }
  };

  const collapseNode = (nodeId) => {
    const source = `expand:${nodeId}`;
    expandedNodeIds.delete(nodeId);
    for (const edgeId of Array.from(edgeSources.keys())) {
      if (forgetSource(edgeSources, edgeId, source)) {
        allEdges.delete(edgeId);
      }
    }
    for (const currentNodeId of Array.from(nodeSources.keys())) {
      if (currentNodeId === nodeId) {
        forgetSource(nodeSources, currentNodeId, source);
        continue;
      }
      if (forgetSource(nodeSources, currentNodeId, source)) {
        allNodes.delete(currentNodeId);
        hiddenNodeIds.delete(currentNodeId);
      }
    }
    setGraphStatus("");
    refreshVisibleGraph();
  };

  const expansionParams = (nodeId) => {
    const params = new URLSearchParams(new FormData(graphForm));
    params.set("focus", nodeId);
    params.delete("limit_nodes");
    params.delete("limit_edges");
    params.set("direction", expansionDirectionInput.value || "both");
    params.set("depth", expansionDepthInput.value || "1");
    params.set("color_by", colorByInput?.value || config.colorBy || "class");
    params.set("color_scheme", colorSchemeInput?.value || config.colorScheme || "strong");
    params.set("node_size", String(selectedNodeSize()));
    params.set("edge_width", String(selectedEdgeWidth()));
    params.set("background_color", selectedBackgroundColor());
    params.set("expansion_limit_nodes", String(config.expansionLimitNodes || 250));
    params.set("expansion_limit_edges", String(config.expansionLimitEdges || 500));
    return params;
  };

  const expandNode = async (nodeId) => {
    if (expandedNodeIds.has(nodeId)) {
      collapseNode(nodeId);
      return;
    }
    if (loadingNodeIds.has(nodeId)) {
      return;
    }
    loadingNodeIds.add(nodeId);
    setGraphStatus(`Loading neighborhood for ${nodeById.get(nodeId)?.label || nodeId}...`, "loading");
    try {
      const response = await fetch(`${graphDataUrl}?${expansionParams(nodeId).toString()}`);
      if (!response.ok) {
        throw new Error(`Graph expansion failed with HTTP ${response.status}`);
      }
      const payload = await response.json();
      expandedNodeIds.add(nodeId);
      addGraphPayload(payload, `expand:${nodeId}`);
      refreshVisibleGraph();
      if (typeof network.selectNodes === "function") {
        network.selectNodes([nodeId]);
      }
      const summary = payload.summary || {};
      if (summary.truncated) {
        setGraphStatus(`Expanded node, showing ${summary.shown_nodes} of ${summary.total_nodes} nodes and ${summary.shown_edges} of ${summary.total_edges} edges.`, "loading");
      } else {
        setGraphStatus("");
      }
    } catch (error) {
      setGraphStatus(error.message || "Graph expansion failed.", "error");
    } finally {
      loadingNodeIds.delete(nodeId);
    }
  };

  const loadFocusedNode = async (nodeId) => {
    if (loadingNodeIds.has(nodeId)) {
      return;
    }
    loadingNodeIds.add(nodeId);
    setGraphStatus(`Loading ${nodeId}...`, "loading");
    try {
      const response = await fetch(`${graphDataUrl}?${expansionParams(nodeId).toString()}`);
      if (!response.ok) {
        throw new Error(`Graph navigation failed with HTTP ${response.status}`);
      }
      const payload = await response.json();
      addGraphPayload(payload, `navigate:${nodeId}`);
      refreshVisibleGraph();
      setGraphStatus("");
    } catch (error) {
      setGraphStatus(error.message || "Graph navigation failed.", "error");
    } finally {
      loadingNodeIds.delete(nodeId);
    }
  };

  navigateToNode = async (nodeId) => {
    if (!nodeId) {
      return;
    }
    if (hiddenNodeIds.has(nodeId)) {
      unhideNode(nodeId);
    }
    if (!allNodes.has(nodeId)) {
      await loadFocusedNode(nodeId);
    }
    const targetNode = nodeById.get(nodeId);
    if (!targetNode) {
      setGraphStatus(`Could not load ${nodeId}.`, "error");
      return;
    }
    hiddenNodeIds.delete(nodeId);
    refreshVisibleGraph();
    centerNode(nodeId);
    showNodeDetails(targetNode);
  };

  const initialize3dGraph = () => {
    activeGraphView = "3d";
    refreshVisibleGraph = refresh3dGraph;
    network = ForceGraph3D()(container)
      .graphData(visible3dData())
      .nodeLabel("label")
      .nodeColor((node) => node.color)
      .nodeVal((node) => node.val)
      .linkLabel("label")
      .linkWidth((link) => link.width)
      .linkDirectionalArrowLength(3)
      .linkDirectionalArrowRelPos(1)
      .linkColor((link) => link.color || "#9aa4b2")
      .backgroundColor(selectedBackgroundColor())
      .onBackgroundClick(() => {
        nodeDetails.style.display = "none";
      })
      .onNodeClick((node) => {
        const now = Date.now();
        if (last3dClick.id === node.id && now - last3dClick.time < 350) {
          expandNode(node.id);
          last3dClick = { id: null, time: 0 };
          return;
        }
        last3dClick = { id: node.id, time: now };
        const graphNode = nodeById.get(node.id);
        if (graphNode) {
          showNodeDetails(graphNode);
        }
      });
  };

  const initialize2dGraph = () => {
    activeGraphView = "2d";
    nodes = new vis.DataSet(Array.from(allNodes.values()).map(visibleNode));
    edges = new vis.DataSet(Array.from(allEdges.values()).map(visibleEdge));
    refreshVisibleGraph = refresh2dGraph;
    network = new vis.Network(container, { nodes, edges }, {
      nodes: {
        shape: "dot",
        size: 14,
        font: { size: 13, face: "Segoe UI" },
        borderWidth: 1
      },
      edges: {
        arrows: "to",
        color: { color: "#9aa4b2", highlight: "#0b6f85" },
        font: { align: "middle", size: 11, face: "Segoe UI" },
        width: selectedEdgeWidth(),
        smooth: { type: "dynamic" }
      },
      groups,
      interaction: {
        dragNodes: true,
        hover: true,
        navigationButtons: true,
        hideEdgesOnDrag: true,
        hideEdgesOnZoom: true
      },
      physics: {
        enabled: true,
        solver: "forceAtlas2Based",
        forceAtlas2Based: {
          gravitationalConstant: -55,
          centralGravity: 0.015,
          springLength: 125,
          springConstant: 0.08
        },
        stabilization: { iterations: 180 }
      }
    });

    network.once("stabilizationIterationsDone", () => {
      network.setOptions({ physics: { enabled: false } });
    });

    network.on("click", (params) => {
      if (params.nodes.length === 0) {
        nodeDetails.style.display = "none";
        return;
      }
      const node = nodeById.get(params.nodes[0]);
      if (node) {
        showNodeDetails(node);
      }
    });

    network.on("doubleClick", (params) => {
      if (params.nodes.length > 0) {
        expandNode(params.nodes[0]);
      }
    });
  };

  if (currentGraphView === "3d") {
    if (!window.ForceGraph3D) {
      initialize2dGraph();
      setGraphStatus("The 3D graph library could not be loaded from unpkg.com. Showing 2D view instead.", "error");
    } else if (!hasWebGLSupport()) {
      initialize2dGraph();
      setGraphStatus("3D view requires WebGL, but this browser could not create a WebGL context. Showing 2D view instead.", "error");
    } else {
      initialize3dGraph();
    }
  } else {
    initialize2dGraph();
  }

  applyGraphBackground();
  updateHiddenNodeMenu();
  renderClassList();
}());
