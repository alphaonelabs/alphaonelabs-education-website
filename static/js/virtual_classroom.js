document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide icons
    lucide.createIcons();

    // Helper function to darken colors
    function darkenColor(hex, percent) {
        let r = parseInt(hex.substring(1,3), 16);
        let g = parseInt(hex.substring(3,5), 16);
        let b = parseInt(hex.substring(5,7), 16);

        r = Math.floor(r * (100 - percent) / 100);
        g = Math.floor(g * (100 - percent) / 100);
        b = Math.floor(b * (100 - percent) / 100);

        return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
    }

    // Constants - these will be updated when settings are loaded
    let COLORS = {
        WALL: '#FFFFFF',
        FLOOR: '#F5F5F5',
        DESK: '#8B4513',
        CHAIR: '#4B0082',
        BOARD: '#000000'
    };

    let SETTINGS = {
        NUM_ROWS: 5,
        DESKS_PER_ROW: 6,
        HAS_PLANTS: true,
        HAS_WINDOWS: true,
        HAS_BOOKSHELF: true,
        HAS_CLOCK: true,
        HAS_CARPET: true
    };

    // Load settings from form data (which comes from the database)
    function loadSettings() {
        // Read values from the form
        const settings = {
            wall_color: document.getElementById('wallColor').value,
            floor_color: document.getElementById('floorColor').value,
            desk_color: document.getElementById('deskColor').value,
            chair_color: document.getElementById('chairColor').value,
            board_color: document.getElementById('boardColor').value,
            number_of_rows: parseInt(document.getElementById('numRows').value),
            desks_per_row: parseInt(document.getElementById('desksPerRow').value),
            has_plants: document.getElementById('hasPlants').checked,
            has_windows: document.getElementById('hasWindows').checked,
            has_bookshelf: document.getElementById('hasBookshelf').checked,
            has_clock: document.getElementById('hasClock').checked,
            has_carpet: document.getElementById('hasCarpet').checked
        };

        // Update the constants
        COLORS.WALL = settings.wall_color;
        COLORS.FLOOR = settings.floor_color;
        COLORS.DESK = settings.desk_color;
        COLORS.CHAIR = settings.chair_color;
        COLORS.BOARD = settings.board_color;

        SETTINGS.NUM_ROWS = settings.number_of_rows;
        SETTINGS.DESKS_PER_ROW = settings.desks_per_row;
        SETTINGS.HAS_PLANTS = settings.has_plants;
        SETTINGS.HAS_WINDOWS = settings.has_windows;
        SETTINGS.HAS_BOOKSHELF = settings.has_bookshelf;
        SETTINGS.HAS_CLOCK = settings.has_clock;
        SETTINGS.HAS_CARPET = settings.has_carpet;

        return settings;
    }

    // Save settings to database via AJAX
    function saveSettings(settings) {
        const data = {
            wallColor: settings.wall_color,
            floorColor: settings.floor_color,
            deskColor: settings.desk_color,
            chairColor: settings.chair_color,
            boardColor: settings.board_color,
            numRows: settings.number_of_rows,
            desksPerRow: settings.desks_per_row,
            hasPlants: settings.has_plants,
            hasWindows: settings.has_windows,
            hasBookshelf: settings.has_bookshelf,
            hasClock: settings.has_clock,
            hasCarpet: settings.has_carpet
        };

        fetch(window.location.href, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log('Customization saved successfully');
            }
        })
        .catch(error => console.error('Error saving customization:', error));
    }

    // Update form values to match settings
    function updateFormValues(settings) {
        // Update color inputs
        document.getElementById('wallColor').value = settings.wall_color;
        document.getElementById('wallColorValue').textContent = settings.wall_color;
        
        document.getElementById('floorColor').value = settings.floor_color;
        document.getElementById('floorColorValue').textContent = settings.floor_color;
        
        document.getElementById('deskColor').value = settings.desk_color;
        document.getElementById('deskColorValue').textContent = settings.desk_color;
        
        document.getElementById('chairColor').value = settings.chair_color;
        document.getElementById('chairColorValue').textContent = settings.chair_color;
        
        document.getElementById('boardColor').value = settings.board_color;
        document.getElementById('boardColorValue').textContent = settings.board_color;

        // Update range inputs
        const numRowsInput = document.getElementById('numRows');
        const numRowsValue = document.getElementById('numRowsValue');
        if (numRowsInput && numRowsValue) {
            numRowsInput.value = settings.number_of_rows;
            numRowsValue.textContent = settings.number_of_rows;
        }
        
        const desksPerRowInput = document.getElementById('desksPerRow');
        const desksPerRowValue = document.getElementById('desksPerRowValue');
        if (desksPerRowInput && desksPerRowValue) {
            desksPerRowInput.value = settings.desks_per_row;
            desksPerRowValue.textContent = settings.desks_per_row;
        }

        // Update checkboxes
        const checkboxes = {
            'hasPlants': settings.has_plants,
            'hasWindows': settings.has_windows,
            'hasBookshelf': settings.has_bookshelf,
            'hasClock': settings.has_clock,
            'hasCarpet': settings.has_carpet
        };

        Object.entries(checkboxes).forEach(([id, value]) => {
            const checkbox = document.getElementById(id);
            if (checkbox) {
                checkbox.checked = value;
            }
        });
    }

    // State management
    const state = {
        settings: loadSettings(),
        character: {
            position: { x: 400, y: 300 },
            velocity: { x: 0, y: 0 },
            direction: 'down',
            isMoving: false,
            walkFrame: 0
        },
        keysPressed: {},
        lastUpdateTime: Date.now()
    };

    // DOM elements
    const classroomContainer = document.getElementById('classroomContainer');
    const controlPanel = document.getElementById('controlPanel');
    const toggleControls = document.getElementById('toggleControls');

    // Event listeners for controls
    toggleControls.addEventListener('click', () => {
        controlPanel.classList.toggle('hidden');
        toggleControls.querySelector('span').textContent = 
            controlPanel.classList.contains('hidden') ? 'Show Controls' : 'Hide Controls';
    });

    // Color input handlers
    document.querySelectorAll('input[type="color"]').forEach(input => {
        input.addEventListener('input', (e) => {
            const setting = e.target.id.replace(/([A-Z])/g, '_$1').toLowerCase();
            state.settings[setting] = e.target.value;
            document.getElementById(e.target.id + 'Value').textContent = e.target.value;
            saveSettings(state.settings);
            renderClassroom();
        });
    });

    // Range input handlers
    document.querySelectorAll('input[type="range"]').forEach(input => {
        input.addEventListener('input', (e) => {
            const mapping = {
                'numRows': 'number_of_rows',
                'desksPerRow': 'desks_per_row'
            };
            const setting = mapping[e.target.id] || e.target.id.replace(/([A-Z])/g, '_$1').toLowerCase();
            state.settings[setting] = parseInt(e.target.value);
            document.getElementById(e.target.id + 'Value').textContent = e.target.value;
            saveSettings(state.settings);
            renderClassroom();
        });
    });

    // Checkbox handlers
    document.querySelectorAll('input[type="checkbox"]').forEach(input => {
        input.addEventListener('change', (e) => {
            const setting = e.target.id.replace(/([A-Z])/g, '_$1').toLowerCase();
            state.settings[setting] = e.target.checked;
            saveSettings(state.settings);
            renderClassroom();
        });
    });

    // Movement handlers
    window.addEventListener('keydown', (e) => {
        if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
            state.keysPressed[e.key] = true;
            e.preventDefault();
        }
    });

    window.addEventListener('keyup', (e) => {
        if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
            state.keysPressed[e.key] = false;
            e.preventDefault();
        }
    });

    // Rendering functions
    function renderClassroom() {
        classroomContainer.innerHTML = '';
        renderWalls();
        renderFloor();
        renderCarpet();
        renderTeacherDesk();
        renderDesksAndChairs();
        renderWhiteboard();
        renderWindows();
        renderBookshelf();
        renderClock();
        renderPlants();
        renderDoor();
        renderCharacter();
    }

    function renderWalls() {
        const frontWall = document.createElement('div');
        frontWall.className = 'absolute transition-colors duration-300';
        frontWall.style.cssText = `
            width: 100%;
            height: 39%;
            background-color: ${state.settings.wall_color};
            top: 0;
            left: 0;
            z-index: 1;
            border-bottom: 6px solid #a0a0a0;
        `;
        classroomContainer.appendChild(frontWall);

        const sideWall1 = document.createElement('div');
        sideWall1.className = 'absolute transition-colors duration-300';
        sideWall1.style.cssText = `
            width: 15%;
            height: 39%;
            background-color: ${darkenColor(state.settings.wall_color, 20)};
            top: 0;
            right: 0;
            z-index: 2;
            border-left: 6px solid #a0a0a0;
            border-bottom: 6px solid #a0a0a0;
        `;
        classroomContainer.appendChild(sideWall1);
        const sideWall2 = document.createElement('div');
        sideWall2.className = 'absolute transition-colors duration-300';
        sideWall2.style.cssText = `
            width: 15%;
            height: 39%;
            background-color: ${darkenColor(state.settings.wall_color, 20)};
            top: 0;
            left: 0;
            z-index: 2;
            border-left: 6px solid #a0a0a0;
            border-bottom: 6px solid #a0a0a0;
        `;
        classroomContainer.appendChild(sideWall2);
    }

    function renderFloor() {
        const floor = document.createElement('div');
        floor.className = 'absolute transition-colors duration-300';
        floor.style.cssText = `
            width: 100%;
            height: 60%;
            background-color: ${state.settings.floor_color};
            bottom: 0;
            left: 0;
            z-index: 3;
            transform: perspective(1000px) rotateX(30deg);
            transform-origin: bottom;
            background-image: linear-gradient(90deg, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.1) 1%, rgba(0,0,0,0) 1%, rgba(0,0,0,0) 100%), linear-gradient(rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.1) 1%, rgba(0,0,0,0) 1%, rgba(0,0,0,0) 100%);
            background-size: 40px 40px;
        `;
        classroomContainer.appendChild(floor);
    }

    function renderCarpet() {
        if (!state.settings.has_carpet) return;
        
        const carpet = document.createElement('div');
        carpet.className = 'absolute rounded-lg transition-all duration-300';
        carpet.style.cssText = `
            width: 65%;
            height: 18%;
            background-color: #8B008B;
            opacity: 0.15;
            left: 17.5%;
            top: 40%;
            z-index: 5;
            background-image: repeating-linear-gradient(45deg, rgba(255,255,255,0.1) 0, rgba(255,255,255,0.1) 10px, transparent 10px, transparent 20px);
            transform: perspective(1000px) rotateX(30deg);
            transform-origin: center top;
        `;
        classroomContainer.appendChild(carpet);
    }

    function renderTeacherDesk() {
        const desk = document.createElement('div');
        desk.className = 'absolute transition-colors duration-300 shadow-lg';
        desk.style.cssText = `
            width: 140px;
            height: 70px;
            background-color: ${darkenColor(state.settings.desk_color, 10)};
            left: 10%;
            top: 30%;
            z-index: 8;
            transform: perspective(500px) rotateX(30deg);
            border-radius: 3px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        `;

        // Desk items
        const paper = document.createElement('div');
        paper.className = 'absolute top-2 left-4 w-8 h-10 bg-white rounded-sm shadow-sm transform rotate-10';
        desk.appendChild(paper);

        const apple = document.createElement('div');
        apple.className = 'absolute top-4 left-14 w-6 h-6 bg-red-600 rounded-full shadow-sm';
        desk.appendChild(apple);

        const pen = document.createElement('div');
        pen.className = 'absolute top-3 right-4 w-4 h-8 bg-blue-800 rounded-sm shadow-sm';
        desk.appendChild(pen);

        // Desk legs
        ['left-4', 'right-4', 'left-20', 'right-20'].forEach(position => {
            const leg = document.createElement('div');
            leg.className = `absolute bottom-0 ${position} w-3 h-12 bg-gray-800`;
            leg.style.transform = 'translateY(100%)';
            desk.appendChild(leg);
        });

        classroomContainer.appendChild(desk);
    }

    function renderDesksAndChairs() {
        const { number_of_rows, desks_per_row } = state.settings;
        const roomWidth = classroomContainer.clientWidth * 0.8;
        const roomDepth = classroomContainer.clientHeight * 0.8;
        
        const startX = classroomContainer.clientWidth * 0.1;
        const startY = classroomContainer.clientHeight * 0.5;
        
        const deskWidth = Math.min(80, roomWidth / desks_per_row);
        const deskDepth = Math.min(60, roomDepth / number_of_rows);
        
        const spacingX = roomWidth / desks_per_row;
        const spacingY = roomDepth / number_of_rows;

        for (let row = 0; row < number_of_rows; row++) {
            for (let col = 0; col < desks_per_row; col++) {
                const x = startX + col * spacingX;
                const y = startY + row * spacingY * 0.6;
                const zIndex = 10 + (number_of_rows - row);

                // Create desk-chair set container
                const deskChairSet = document.createElement('div');
                deskChairSet.className = 'desk-chair-set absolute';
                deskChairSet.style.cssText = `left: ${x}px; top: ${y}px;`;

                // Create desk
                const desk = document.createElement('div');
                desk.className = 'absolute transition-colors duration-300 shadow-md';
                desk.style.cssText = `
                    width: ${deskWidth}px;
                    height: ${deskDepth}px;
                    background-color: ${state.settings.desk_color};
                    transform: perspective(500px) rotateX(30deg);
                    z-index: ${zIndex};
                    border-radius: 2px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                `;

                // Add desk legs
                ['left-2', 'right-2'].forEach(position => {
                    const leg = document.createElement('div');
                    leg.className = `absolute bottom-0 ${position} w-2 h-10 bg-gray-700`;
                    leg.style.transform = 'translateY(100%)';
                    desk.appendChild(leg);
                });

                // Create chair
                const chair = document.createElement('div');
                chair.className = 'absolute transition-colors duration-300 shadow-md';
                chair.style.cssText = `
                    width: ${deskWidth * 0.6}px;
                    height: ${deskDepth * 0.5}px;
                    background-color: ${state.settings.chair_color};
                    top: ${deskDepth + 5}px;
                    left: ${deskWidth * 0.2}px;
                    z-index: ${zIndex - 1};
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    border-bottom-left-radius: 3px;
                    border-bottom-right-radius: 3px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                `;

                // Add chair back
                const chairBack = document.createElement('div');
                chairBack.className = 'absolute top-0 left-0 right-0 h-8 bg-gray-800';
                chairBack.style.cssText = `
                    transform: translateY(-80%);
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                `;
                chair.appendChild(chairBack);

                deskChairSet.appendChild(desk);
                deskChairSet.appendChild(chair);
                classroomContainer.appendChild(deskChairSet);
            }
        }
    }

    function renderWhiteboard() {
        const boardContainer = document.createElement('div');
        boardContainer.className = 'absolute';
        boardContainer.style.cssText = `
            z-index: 10;
            top: 7%;
            width: 100%;
        `;

        const board = document.createElement('div');
        board.className = 'mx-auto transition-colors duration-300 shadow-lg relative';
        board.style.cssText = `
            width: 65%;
            height: ${classroomContainer.clientHeight * 0.2}px;
            background-color: ${state.settings.board_color};
            border: 12px solid #6b4226;
            border-radius: 4px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        `;

        const text = document.createElement('div');
        text.className = 'text-white text-center h-full flex items-center justify-center text-xl font-bold';
        text.textContent = 'Virtual Classroom';
        board.appendChild(text);

        const ledge = document.createElement('div');
        ledge.className = 'absolute -bottom-4 left-0 right-0 h-4 bg-[#8B4513]';
        ledge.style.cssText = `
            transform: perspective(100px) rotateX(45deg);
            transform-origin: top;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        `;
        board.appendChild(ledge);

        boardContainer.appendChild(board);
        classroomContainer.appendChild(boardContainer);
    }

    function renderWindows() {
        if (!state.settings.has_windows) return;

        // Side wall window
        const sideWindow = document.createElement('div');
        sideWindow.className = 'absolute rounded-lg shadow-inner transition-all duration-300 flex items-center justify-center';
        sideWindow.style.cssText = `
            width: 60px;
            height: 100px;
            background-color: #87CEEB;
            right: 1.5%;
            top: 10%;
            z-index: 5;
            border: 8px solid #A0522D;
            box-shadow: inset 0 0 20px rgba(255,255,255,0.5);
            background-image: linear-gradient(135deg, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0) 50%, rgba(255,255,255,0.4) 100%);
        `;
        const windIcon1 = document.createElement('i');
        windIcon1.setAttribute('data-lucide', 'wind');
        windIcon1.className = 'text-white opacity-70';
        sideWindow.appendChild(windIcon1);
        classroomContainer.appendChild(sideWindow);

        // Front wall windows
        [30, 55].forEach(leftPos => {
            const frontWindow = document.createElement('div');
            frontWindow.className = 'absolute rounded-lg shadow-inner transition-all duration-300 flex items-center justify-center';
            frontWindow.style.cssText = `
                width: 80px;
                height: 120px;
                background-color: #87CEEB;
                left: ${leftPos}%;
                top: 12%;
                z-index: 5;
                border: 8px solid #A0522D;
                box-shadow: inset 0 0 20px rgba(255,255,255,0.5);
                background-image: linear-gradient(135deg, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0) 50%, rgba(255,255,255,0.4) 100%);
            `;
            const windIcon = document.createElement('i');
            windIcon.setAttribute('data-lucide', 'wind');
            windIcon.className = 'text-white opacity-70';
            frontWindow.appendChild(windIcon);
            classroomContainer.appendChild(frontWindow);
        });

        // Reinitialize Lucide icons for the new wind icons
        lucide.createIcons();
    }

    function renderBookshelf() {
        if (!state.settings.has_bookshelf) return;

        const bookshelf = document.createElement('div');
        bookshelf.className = 'absolute rounded-sm shadow-lg transition-all duration-300';
        bookshelf.style.cssText = `
            width: 100px;
            height: 140px;
            background-color: #854D0E;
            right: 6%;
            top: 25%;
            z-index: 15;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            border: 1px solid #5c3507;
        `;

        // Add shelves
        [25, 50, 75].forEach(topPos => {
            const shelf = document.createElement('div');
            shelf.className = 'absolute w-full h-2 bg-[#5c3507]';
            shelf.style.top = `${topPos}%`;
            bookshelf.appendChild(shelf);
        });

        // Add books
        const bookColors = ['blue-600', 'red-600', 'green-600', 'purple-600', 'yellow-600', 'indigo-600', 'pink-600'];
        [0, 1, 2].forEach(row => {
            const bookRow = document.createElement('div');
            bookRow.className = 'flex justify-center items-end h-1/4 pb-1';
            if (row > 0) bookRow.classList.add('mt-1');

            for (let i = 0; i < 3; i++) {
                const book = document.createElement('i');
                book.setAttribute('data-lucide', i % 2 === 0 ? 'book' : 'book-open');
                book.className = `text-${bookColors[Math.floor(Math.random() * bookColors.length)]} mx-1`;
                book.style.fontSize = `${16 + Math.random() * 2}px`;
                bookRow.appendChild(book);
            }
            bookshelf.appendChild(bookRow);
        });

        classroomContainer.appendChild(bookshelf);
        lucide.createIcons();
    }

    function renderClock() {
        if (!state.settings.has_clock) return;

        const clock = document.createElement('div');
        clock.className = 'absolute flex items-center justify-center rounded-full shadow-md transition-all duration-300';
        clock.style.cssText = `
            width: 60px;
            height: 60px;
            background-color: #F5F5F5;
            border: 3px solid #333;
            right: 8%;
            top: 13%;
            z-index: 20;
        `;

        const clockIcon = document.createElement('i');
        clockIcon.setAttribute('data-lucide', 'clock');
        clockIcon.className = 'text-gray-800';
        clockIcon.style.width = '40px';
        clockIcon.style.height = '40px';
        clock.appendChild(clockIcon);

        classroomContainer.appendChild(clock);
        lucide.createIcons();
    }

    function renderPlants() {
        if (!state.settings.has_plants) return;

        // Corner plant
        const cornerPlant = document.createElement('div');
        cornerPlant.className = 'absolute transition-all duration-300';
        cornerPlant.style.cssText = `
            right: 10%;
            top: 48%;
            z-index: 16;
        `;
        cornerPlant.innerHTML = `
            <div class="w-16 h-28 flex flex-col items-center">
                <div class="w-12 h-14 bg-green-700 rounded-full -mb-3 z-10"></div>
                <div class="w-14 h-14 bg-green-600 rounded-full -mb-3 z-20"></div>
                <div class="w-16 h-16 bg-green-500 rounded-full -mb-2 z-30"></div>
                <div class="w-8 h-12 bg-amber-700 rounded-md z-0"></div>
            </div>
        `;
        classroomContainer.appendChild(cornerPlant);

        // Front wall plant
        const frontPlant = document.createElement('div');
        frontPlant.className = 'absolute transition-all duration-300';
        frontPlant.style.cssText = `
            right: 0%;
            top: 31.25%;
            z-index: 16;
        `;
        frontPlant.innerHTML = `
            <div class="w-20 h-32 flex flex-col items-center">
                <div class="w-16 h-18 bg-green-600 rounded-full -mb-3 z-10"></div>
                <div class="w-18 h-18 bg-green-500 rounded-full -mb-3 z-20"></div>
                <div class="w-16 h-16 bg-green-400 rounded-full -mb-2 z-30"></div>
                <div class="w-10 h-14 bg-amber-800 rounded-md z-0"></div>
            </div>
        `;
        classroomContainer.appendChild(frontPlant);
    }

    function renderDoor() {
        const door = document.createElement('div');
        door.className = 'absolute transition-all duration-300';
        door.style.cssText = `
            width: 60px;
            height: 120px;
            background-color: #8B4513;
            left: 3%;
            top: 24%;
            z-index: 6;
            border-left: 5px solid #6b4226;
            border-top: 5px solid #6b4226;
            border-bottom: 5px solid #6b4226;
            border-top-left-radius: 5px;
            border-bottom-left-radius: 5px;
        `;

        const doorHandle = document.createElement('div');
        doorHandle.className = 'absolute right-3 top-1/2 w-3 h-3 bg-yellow-600 rounded-full';
        door.appendChild(doorHandle);

        classroomContainer.appendChild(door);
    }

    function renderCharacter() {
        // Remove any existing character first
        const existingCharacter = classroomContainer.querySelector('.character-facing-up, .character-facing-down, .character-facing-left, .character-facing-right');
        if (existingCharacter) {
            existingCharacter.remove();
        }

        const character = document.createElement('div');
        character.className = `absolute transition-transform duration-200 pointer-events-none character-facing-${state.character.direction}`;
        character.style.cssText = `
            left: ${state.character.position.x}px;
            top: ${state.character.position.y}px;
            transform: translate(-50%, -50%);
            z-index: ${Math.floor(state.character.position.y)};
        `;

        // Character design HTML
        character.innerHTML = `
            <div class="relative">
                <div class="flex flex-col items-center">
                    <div class="w-16 h-16 relative">
                        <div class="absolute w-14 h-14 bg-[#FFD9B3] rounded-full top-1 left-1 shadow-md border border-[#E0B088]"></div>
                        ${getCharacterHairHTML()}
                        ${getCharacterFaceHTML()}
                    </div>
                    ${getCharacterBodyHTML()}
                </div>
            </div>
        `;

        classroomContainer.appendChild(character);
    }

    // Helper functions for character rendering
    function getCharacterHairHTML() {
        switch(state.character.direction) {
            case 'down':
                return '<div class="absolute w-14 h-7 bg-[#8B4513] rounded-t-full top-0 left-1"></div>';
            case 'up':
                return '<div class="absolute w-14 h-8 bg-[#8B4513] rounded-t-full top-0 left-1"></div>';
            case 'left':
                return `
                    <div class="absolute w-14 h-7 bg-[#8B4513] rounded-t-full top-0 left-1"></div>
                    <div class="absolute w-3 h-8 bg-[#8B4513] rounded-l-full top-4 left-0"></div>
                `;
            case 'right':
                return `
                    <div class="absolute w-14 h-7 bg-[#8B4513] rounded-t-full top-0 left-1"></div>
                    <div class="absolute w-3 h-8 bg-[#8B4513] rounded-r-full top-4 right-0"></div>
                `;
            default:
                return '';
        }
    }

    function getCharacterFaceHTML() {
        switch(state.character.direction) {
            case 'down':
                return `
                    <div class="absolute top-6 left-4 w-2 h-2 bg-[#302825] rounded-full"></div>
                    <div class="absolute top-6 right-4 w-2 h-2 bg-[#302825] rounded-full"></div>
                    <div class="absolute top-10 left-6 w-4 h-1 bg-[#CC6666] rounded-full"></div>
                `;
            case 'up':
                return '<div class="absolute top-3 left-3 w-8 h-2 bg-[#8B4513] rounded-full"></div>';
            case 'left':
                return `
                    <div class="absolute top-6 left-4 w-2 h-2 bg-[#302825] rounded-full"></div>
                    <div class="absolute top-10 left-3 w-2 h-1 bg-[#CC6666] rounded-full"></div>
                `;
            case 'right':
                return `
                    <div class="absolute top-6 right-4 w-2 h-2 bg-[#302825] rounded-full"></div>
                    <div class="absolute top-10 right-3 w-2 h-1 bg-[#CC6666] rounded-full"></div>
                `;
            default:
                return '';
        }
    }

    function getCharacterBodyHTML() {
        const isMoving = state.character.isMoving;
        const walkFrame = state.character.walkFrame;
        
        return `
            <div class="relative w-20 h-24 -mt-4">
                <div class="w-16 h-16 bg-blue-600 rounded-md mx-auto ${isMoving ? 'animate-pulse' : ''}"
                     style="background-color: ${isMoving ? '#4169E1' : '#3457D1'}">
                    <div class="absolute inset-x-0 top-0 h-4 bg-blue-700 rounded-t-md"></div>
                    <div class="absolute inset-x-4 top-4 h-8 w-8 bg-blue-500 rounded-md"></div>
                </div>
                ${getCharacterArmsHTML()}
                ${getCharacterLegsHTML()}
                <div class="absolute bottom-0 w-12 h-3 bg-black opacity-30 rounded-full -z-10 transform translate-y-2"></div>
            </div>
        `;
    }

    function getCharacterArmsHTML() {
        const walkFrame = state.character.walkFrame;
        switch(state.character.direction) {
            case 'down':
            case 'up':
                return `
                    <div class="absolute left-0 top-2 w-4 h-10 bg-[#FFD9B3] rounded-full transform ${walkFrame % 2 === 0 ? 'rotate-6' : '-rotate-6'}"></div>
                    <div class="absolute right-0 top-2 w-4 h-10 bg-[#FFD9B3] rounded-full transform ${walkFrame % 2 === 0 ? '-rotate-6' : 'rotate-6'}"></div>
                `;
            case 'left':
                return '<div class="absolute left-1 top-2 w-4 h-10 bg-[#FFD9B3] rounded-full transform ${walkFrame % 2 === 0 ? "translate-y-1" : "-translate-y-1"}"></div>';
            case 'right':
                return '<div class="absolute right-1 top-2 w-4 h-10 bg-[#FFD9B3] rounded-full transform ${walkFrame % 2 === 0 ? "translate-y-1" : "-translate-y-1"}"></div>';
            default:
                return '';
        }
    }

    function getCharacterLegsHTML() {
        const isMoving = state.character.isMoving;
        const walkFrame = state.character.walkFrame;
        
        return `
            <div class="absolute bottom-0 left-4 w-12 h-2 bg-transparent flex justify-between">
                <div class="w-4 h-10 bg-[#1F456E] rounded-md transform origin-top ${
                    isMoving ? (walkFrame % 2 === 0 ? 'translate-y-0' : 'translate-y-1') : ''
                }"></div>
                <div class="w-4 h-10 bg-[#1F456E] rounded-md transform origin-top ${
                    isMoving ? (walkFrame % 2 === 0 ? 'translate-y-1' : 'translate-y-0') : ''
                }"></div>
            </div>
            <div class="absolute bottom-0 left-3 w-14 h-2 bg-transparent flex justify-between">
                <div class="w-5 h-3 bg-[#222] rounded-md transform ${
                    isMoving ? (walkFrame % 2 === 0 ? 'translate-y-0' : 'translate-y-1') : ''
                }"></div>
                <div class="w-5 h-3 bg-[#222] rounded-md transform ${
                    isMoving ? (walkFrame % 2 === 0 ? 'translate-y-1' : 'translate-y-0') : ''
                }"></div>
            </div>
        `;
    }

    // Character animation loop
    function updateCharacter() {
        const now = Date.now();
        const deltaTime = (now - state.lastUpdateTime) / 16.67;
        state.lastUpdateTime = now;

        const friction = 0.85;
        const acceleration = 0.8;
        let newVx = state.character.velocity.x;
        let newVy = state.character.velocity.y;

        if (state.keysPressed.ArrowUp) {
            newVy -= acceleration;
            state.character.direction = 'up';
        }
        if (state.keysPressed.ArrowDown) {
            newVy += acceleration;
            state.character.direction = 'down';
        }
        if (state.keysPressed.ArrowLeft) {
            newVx -= acceleration;
            state.character.direction = 'left';
        }
        if (state.keysPressed.ArrowRight) {
            newVx += acceleration;
            state.character.direction = 'right';
        }

        newVx *= friction;
        newVy *= friction;

        const containerRect = classroomContainer.getBoundingClientRect();
        const paddingX = 40;
        const paddingY = 40;

        let newX = state.character.position.x + newVx * deltaTime;
        let newY = state.character.position.y + newVy * deltaTime;

        if (newX < paddingX) {
            newX = paddingX;
            newVx = 0;
        }
        if (newX > containerRect.width - paddingX) {
            newX = containerRect.width - paddingX;
            newVx = 0;
        }
        if (newY < paddingY) {
            newY = paddingY;
            newVy = 0;
        }
        if (newY > containerRect.height - paddingY) {
            newY = containerRect.height - paddingY;
            newVy = 0;
        }

        state.character.isMoving = Math.abs(newVx) > 0.1 || Math.abs(newVy) > 0.1;

        if (state.character.isMoving && now % 150 < 30) {
            state.character.walkFrame = (state.character.walkFrame + 1) % 4;
        } else if (!state.character.isMoving) {
            state.character.walkFrame = 0;
        }

        state.character.position = { x: newX, y: newY };
        state.character.velocity = { x: newVx, y: newVy };

        renderCharacter();
        requestAnimationFrame(updateCharacter);
    }

    // Get CSRF token from cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Initial render and start animation loop
    renderClassroom();
    requestAnimationFrame(updateCharacter);
}); 