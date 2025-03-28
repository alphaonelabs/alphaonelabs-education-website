// For learning-maps/detail.js
document.addEventListener('DOMContentLoaded', function() {
    const mapContainer = document.getElementById('learning-map-container');
    if (!mapContainer) return;

    const mapSlug = mapContainer.dataset.mapSlug;

    // Fetch map data
    fetch(`/learning-maps/${mapSlug}/data/`)
        .then(response => response.json())
        .then(data => renderLearningMap(data))
        .catch(error => {
            console.error('Error loading learning map data:', error);
            mapContainer.innerHTML = '<div class="alert alert-danger">Error loading learning map data</div>';
        });

    function renderLearningMap(data) {
        // Create SVG element
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', '400');
        svg.setAttribute('class', 'learning-map-svg');

        // Sort nodes by order
        const nodes = data.nodes.sort((a, b) => a.order - b.order);

        // Calculate path and node positions
        const pathStartX = 50;
        const pathEndX = 800;
        const pathY = 200;
        const nodeRadius = 25;

        // Draw the main path
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', `M ${pathStartX} ${pathY} L ${pathEndX} ${pathY}`);
        path.setAttribute('stroke', 'var(--color-gray-300, #d1d5db)');
        path.setAttribute('stroke-width', '4');
        path.setAttribute('fill', 'none');
        svg.appendChild(path);

        // Calculate spacing between nodes
        const totalNodesCount = nodes.length || 1;
        const spacing = (pathEndX - pathStartX) / (totalNodesCount);

        // Draw nodes
        nodes.forEach((node, index) => {
            const x = pathStartX + spacing * (index + 0.5);
            const y = node.y || pathY;

            // Create node group
            const nodeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            nodeGroup.setAttribute('class', 'map-node');
            nodeGroup.setAttribute('data-node-id', node.id);
            nodeGroup.setAttribute('data-node-type', node.type);

            // Determine node color based on type and completion
            let nodeColor;
            if (node.completed) {
                nodeColor = 'var(--color-green-500, #10b981)';
            } else {
                switch (node.type) {
                    case 'tracker':
                        nodeColor = `var(--color-${node.color || 'blue-500'}, #3b82f6)`;
                        break;
                    case 'course':
                        nodeColor = 'var(--color-blue-500, #3b82f6)';
                        break;
                    case 'milestone':
                        nodeColor = `var(--color-${node.color || 'yellow-500'}, #f59e0b)`;
                        break;
                    default:
                        nodeColor = 'var(--color-gray-500, #6b7280)';
                }
            }

            // Draw node circle
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', x);
            circle.setAttribute('cy', y);
            circle.setAttribute('r', nodeRadius);
            circle.setAttribute('fill', nodeColor);
            nodeGroup.appendChild(circle);

            // Draw progress arc if not complete
            if (!node.completed && node.progress > 0) {
                drawProgressArc(nodeGroup, x, y, nodeRadius, node.progress);
            }

            // Add node title
            const title = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            title.setAttribute('x', x);
            title.setAttribute('y', y + nodeRadius + 20);
            title.setAttribute('text-anchor', 'middle');
            title.setAttribute('fill', 'currentColor');
            title.setAttribute('class', 'text-sm font-medium');
            title.textContent = shortenText(node.title, 20);
            nodeGroup.appendChild(title);

            // Add progress percentage
            const progressText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            progressText.setAttribute('x', x);
            progressText.setAttribute('y', y);
            progressText.setAttribute('text-anchor', 'middle');
            progressText.setAttribute('dominant-baseline', 'middle');
            progressText.setAttribute('fill', 'white');
            progressText.setAttribute('class', 'text-xs font-bold');
            progressText.textContent = `${Math.round(node.progress)}%`;
            nodeGroup.appendChild(progressText);

            // Add node type label
            const typeLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            typeLabel.setAttribute('x', x);
            typeLabel.setAttribute('y', y - nodeRadius - 10);
            typeLabel.setAttribute('text-anchor', 'middle');
            typeLabel.setAttribute('fill', 'currentColor');
            typeLabel.setAttribute('class', 'text-xs');
            typeLabel.textContent = getNodeTypeLabel(node.type);
            nodeGroup.appendChild(typeLabel);

            // Add click event
            nodeGroup.addEventListener('click', () => showNodeDetails(node));
            nodeGroup.style.cursor = 'pointer';

            svg.appendChild(nodeGroup);
        });

        // Add map title
        const title = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        title.setAttribute('x', (pathStartX + pathEndX) / 2);
        title.setAttribute('y', 30);
        title.setAttribute('text-anchor', 'middle');
        title.setAttribute('fill', 'currentColor');
        title.setAttribute('class', 'text-xl font-bold');
        title.textContent = data.title;
        svg.appendChild(title);

        // Add legend
        addLegend(svg, pathStartX, pathEndX, pathY + 100);

        // Replace loading indicator with the SVG
        mapContainer.innerHTML = '';
        mapContainer.appendChild(svg);
    }

    function drawProgressArc(group, cx, cy, radius, percentage) {
        const startAngle = -Math.PI / 2; // Start from top
        const endAngle = startAngle + (2 * Math.PI * percentage / 100);
        const largeArcFlag = percentage > 50 ? 1 : 0;

        const x1 = cx + radius * Math.cos(startAngle);
        const y1 = cy + radius * Math.sin(startAngle);
        const x2 = cx + radius * Math.cos(endAngle);
        const y2 = cy + radius * Math.sin(endAngle);

        const pathData = `M ${cx} ${cy} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`;

        const arc = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        arc.setAttribute('d', pathData);
        arc.setAttribute('fill', 'var(--color-green-500, #10b981)');
        group.appendChild(arc);
    }

    function addLegend(svg, startX, endX, y) {
        const legendGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        legendGroup.setAttribute('class', 'legend');

        const items = [
            { color: 'var(--color-green-500, #10b981)', label: 'Completed' },
            { color: 'var(--color-blue-500, #3b82f6)', label: 'Course' },
            { color: 'var(--color-purple-500, #8b5cf6)', label: 'Progress Tracker' },
            { color: 'var(--color-yellow-500, #f59e0b)', label: 'Milestone' }
        ];

        const itemWidth = 120;
        const startLegendX = (startX + endX - (items.length * itemWidth)) / 2;

        items.forEach((item, index) => {
            const x = startLegendX + (index * itemWidth);

            // Circle
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', x + 10);
            circle.setAttribute('cy', y);
            circle.setAttribute('r', 6);
            circle.setAttribute('fill', item.color);
            legendGroup.appendChild(circle);

            // Label
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', x + 25);
            text.setAttribute('y', y);
            text.setAttribute('dominant-baseline', 'middle');
            text.setAttribute('fill', 'currentColor');
            text.setAttribute('class', 'text-xs');
            text.textContent = item.label;
            legendGroup.appendChild(text);
        });

        svg.appendChild(legendGroup);
    }

    function getNodeTypeLabel(type) {
        switch (type) {
            case 'tracker': return 'Progress Tracker';
            case 'course': return 'Course';
            case 'milestone': return 'Milestone';
            default: return 'Node';
        }
    }

    function shortenText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    }

    function showNodeDetails(node) {
        // Create a modal for displaying node details
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.id = 'node-details-modal';

        // Create modal content
        const modalContent = document.createElement('div');
        modalContent.className = 'bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6';

        // Node type badge
        const typeBadge = document.createElement('span');
        typeBadge.className = `inline-block px-2 py-1 text-xs rounded text-white mb-4 ${getNodeTypeBadgeClass(node.type)}`;
        typeBadge.textContent = getNodeTypeLabel(node.type);

        // Title
        const title = document.createElement('h3');
        title.className = 'text-xl font-bold mb-2';
        title.textContent = node.title;

        // Progress bar
        const progressContainer = document.createElement('div');
        progressContainer.className = 'w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 mb-4';

        const progressBar = document.createElement('div');
        progressBar.className = `bg-${node.color || 'blue-600'} h-2.5 rounded-full`;
        progressBar.style.width = `${node.progress}%`;
        progressContainer.appendChild(progressBar);

        // Progress text
        const progressText = document.createElement('p');
        progressText.className = 'text-sm text-gray-500 dark:text-gray-400 mb-4';
        progressText.textContent = `Progress: ${Math.round(node.progress)}%`;

        // Description if available
        let description = null;
        if (node.description) {
            description = document.createElement('p');
            description.className = 'text-gray-600 dark:text-gray-300 mb-4';
            description.textContent = node.description;
        }

        // Details based on node type
        const details = document.createElement('div');
        details.className = 'mb-4';

        if (node.type === 'tracker') {
            details.innerHTML = `
                <p class="text-sm"><span class="font-medium">Current value:</span> ${node.current_value}</p>
                <p class="text-sm"><span class="font-medium">Target value:</span> ${node.target_value}</p>
            `;
        } else if (node.type === 'course') {
            details.innerHTML = `
                <p class="text-sm"><span class="font-medium">Course:</span> ${node.course_title}</p>
                <a href="/courses/${node.course_slug}" class="text-blue-600 dark:text-blue-400 hover:underline text-sm">View course</a>
            `;
        } else if (node.type === 'milestone') {
            details.innerHTML = `
                <p class="text-sm"><span class="font-medium">Current value:</span> ${node.current_value}</p>
                <p class="text-sm"><span class="font-medium">Target value:</span> ${node.target_value}</p>
            `;

            // Add update form for milestones if we're the owner
            if (document.getElementById('is-owner-indicator')) {
                const updateForm = document.createElement('form');
                updateForm.action = `/learning-maps/nodes/${node.id}/update/`;
                updateForm.method = 'post';
                updateForm.className = 'mt-4';

                updateForm.innerHTML = `
                    <input type="hidden" name="csrfmiddlewaretoken" value="${getCsrfToken()}">
                    <div class="mb-3">
                        <label for="current_value" class="block text-sm font-medium mb-1">Update progress:</label>
                        <input type="number" name="current_value" id="current_value" value="${node.current_value}"
                               min="0" max="${node.target_value}"
                               class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md">
                    </div>
                    <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        Update Progress
                    </button>
                `;

                details.appendChild(updateForm);
            }
        }

        // Close button
        const closeButton = document.createElement('button');
        closeButton.className = 'mt-4 px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded hover:bg-gray-300 dark:hover:bg-gray-600';
        closeButton.textContent = 'Close';
        closeButton.onclick = () => {
            document.body.removeChild(modal);
        };

        // Add all elements to modal content
        modalContent.appendChild(typeBadge);
        modalContent.appendChild(title);
        modalContent.appendChild(progressContainer);
        modalContent.appendChild(progressText);
        if (description) modalContent.appendChild(description);
        modalContent.appendChild(details);
        modalContent.appendChild(closeButton);

        modal.appendChild(modalContent);

        // Close modal when clicking outside
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                document.body.removeChild(modal);
            }
        });

        document.body.appendChild(modal);
    }

    function getNodeTypeBadgeClass(type) {
        switch (type) {
            case 'tracker': return 'bg-purple-600';
            case 'course': return 'bg-blue-600';
            case 'milestone': return 'bg-yellow-600';
            default: return 'bg-gray-600';
        }
    }

    function getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
});
