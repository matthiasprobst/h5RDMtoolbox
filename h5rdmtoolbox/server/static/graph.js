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
  let hideNode = () => {};
  let unhideNode = () => {};
  let refreshVisibleGraph = () => {};
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

  const visibleNode = (node) => ({
    ...node,
    group: selectedNodeGroup(node),
    label: renderedLabelsEnabled() ? node.label : undefined,
    title: node.label,
    borderWidth: node.expandable ? 3 : 1,
    size: selectedNodeSize() + (node.expandable ? 3 : 0)
  });

  const visibleEdge = (edge) => ({
    ...edge,
    id: edgeKey(edge),
    label: renderedLabelsEnabled() ? edge.label : undefined,
    title: edge.label,
    width: selectedEdgeWidth()
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

  const showNodeDetails = (node) => {
    const literals = node.literals || [];
    const hiddenNeighborText = node.hidden_neighbor_count
      ? `<p class="no-literals">${node.hidden_neighbor_count} more connected node(s). Double-click to expand.</p>`
      : "";
    const literalRows = literals.length
      ? `<dl>${literals.map((literal) => `<dt>${escapeHtml(literal.predicate)}</dt><dd>${escapeHtml(literal.value)}</dd>`).join("")}</dl>`
      : '<p class="no-literals">No literal values are available for this node.</p>';
    const localLink = node.local_href
      ? `<a class="node-link" href="${escapeHtml(node.local_href)}" target="_blank" rel="noopener">Open local TTL</a>`
      : "";
    nodeDetails.innerHTML = `<div class="node-details-header"><h2>${escapeHtml(node.label)}</h2><button type="button" class="hide-node-button">Hide</button></div>${localLink}${hiddenNeighborText}${literalRows}`;
    nodeDetails.querySelector(".hide-node-button").addEventListener("click", () => {
      hideNode(node.id);
    });
    nodeDetails.style.display = "block";
  };

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
    emptyGraph.style.display = "block";
    return;
  }

  if (!window.vis) {
    emptyGraph.textContent = "The 2D graph library could not be loaded.";
    emptyGraph.style.display = "block";
    return;
  }

  const groups = allGroups;

  const groupColor = (node) => {
    const group = groups[selectedNodeGroup(node)] || {};
    if (typeof group.color === "string") {
      return group.color;
    }
    return group.color?.background || "#0b6f85";
  };

  const visible3dNode = (node) => ({
    ...node,
    name: node.label,
    val: (selectedNodeSize() / 14 * 3) + (node.expandable ? 2 : 0),
    color: groupColor(node)
  });

  const visible3dLink = (edge) => ({
    ...edge,
    source: edge.from,
    target: edge.to,
    width: selectedEdgeWidth()
  });

  const visible3dData = () => ({
    nodes: Array.from(allNodes.values())
      .filter((node) => !hiddenNodeIds.has(node.id))
      .map(visible3dNode),
    links: Array.from(allEdges.values())
      .filter((edge) => !hiddenNodeIds.has(edge.from) && !hiddenNodeIds.has(edge.to))
      .map(visible3dLink)
  });

  const refresh2dGraph = () => {
    rememberPositions();
    network.setOptions({ groups });
    nodes.clear();
    nodes.add(Array.from(allNodes.values())
      .filter((node) => !hiddenNodeIds.has(node.id))
      .map(visibleNodeWithPosition));
    edges.clear();
    edges.add(Array.from(allEdges.values())
      .filter((edge) => !hiddenNodeIds.has(edge.from) && !hiddenNodeIds.has(edge.to))
      .map(visibleEdge));
    updateHiddenNodeMenu();
  };

  const refresh3dGraph = () => {
    applyGraphBackground();
    network.graphData(visible3dData());
    updateHiddenNodeMenu();
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
      const restoredEdges = Array.from(allEdges.values())
        .filter((edge) => !hiddenNodeIds.has(edge.from) && !hiddenNodeIds.has(edge.to))
        .map(visibleEdge);
      edges.update(restoredEdges);
      updateHiddenNodeMenu();
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
      .linkColor(() => "#9aa4b2")
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
}());
