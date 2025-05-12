// Virtual Classroom Game using Phaser
// Main game configuration
const config = {
  type: Phaser.AUTO,
  parent: 'classroom-game',
  width: 1024,
  height: 576,
  pixelArt: true,
  physics: {
    default: 'arcade',
    arcade: {
      gravity: { y: 0 },
      debug: true  // Enable physics debug
    }
  },
  scene: {
    preload: preload,
    create: create,
    update: update
  }
};

// Create the game instance
const game = new Phaser.Game(config);

// Game variables
let player;
let cursors;
let interactKey;
let interactButton;
let interactText;
let interactableObjects = [];
let chairsOccupancy = {};
let isNearInteractable = false;
let currentInteractable = null;
let csrfToken = '';
let debugText; // For showing debug info
let isPlayerSeated = false;
let currentChair = null;
let currentCharacterKey = 'character';

// Preload game assets
function preload() {
  // Add loading text
  this.add.text(20, 20, 'Loading game...', { fill: '#000' });

  // Add error handling for asset loading
  this.load.on('loaderror', function(fileObj) {
    console.error('Error loading asset:', fileObj.src);
  });

  // Character assets
  this.load.spritesheet('character', '/static/images/classroom/character.png', { 
    frameWidth: 64, 
    frameHeight: 64 
  });
  this.load.spritesheet('character-2', '/static/images/classroom/character-2.png', { 
    frameWidth: 64, 
    frameHeight: 64 
  });
  
  // Classroom assets
  this.load.image('tiles', '/static/images/classroom/classroom_tiles.png');
  this.load.image('whiteboard', '/static/images/classroom/whiteboard.png');
  this.load.image('chair', '/static/images/classroom/chair.png');
  this.load.image('chair-taken', '/static/images/classroom/chair-taken.png');
  this.load.image('desk', '/static/images/classroom/desk.png');
  this.load.image('window', '/static/images/classroom/window.png');
  this.load.image('door', '/static/images/classroom/door.png');
  this.load.image('interaction_icon', '/static/images/classroom/interaction_icon.png');

  // Add progress bar
  let progressBar = this.add.graphics();
  let progressBox = this.add.graphics();
  progressBox.fillStyle(0x222222, 0.8);
  progressBox.fillRect(240, 270, 320, 50);
  
  this.load.on('progress', function (value) {
    progressBar.clear();
    progressBar.fillStyle(0x00ff00, 1);
    progressBar.fillRect(250, 280, 300 * value, 30);
  });
}

// Create game objects and setup
function create() {
  // Add debug text
  debugText = this.add.text(16, 16, 'Debug info', { fontSize: '18px', fill: '#000' });
  debugText.setScrollFactor(0);
  debugText.setDepth(1000);
  
  try {
    // Get CSRF token for AJAX requests
    csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // Create classroom background
    const background = this.add.rectangle(0, 0, config.width, config.height, 0xf0f0f0).setOrigin(0);
    background.setDepth(-1);
    
    // Create classroom objects
    createClassroomObjects(this);
    
    // Create player character
    player = this.physics.add.sprite(400, 300, currentCharacterKey);
    player.setCollideWorldBounds(true);
    player.setSize(20, 30);
    player.setOffset(6, 15);
    
    // Setup camera to follow player
    this.cameras.main.startFollow(player, true, 0.08, 0.08);
    this.cameras.main.setZoom(1.2);
    
    // Create character animations
    createAnimations(this);
    
    // Setup user input
    cursors = this.input.keyboard.createCursorKeys();
    // Add WASD keys
    cursors.w = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.W);
    cursors.a = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.A);
    cursors.s = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.S);
    cursors.d = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.D);
    interactKey = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.E);
    
    // Get DOM elements
    interactButton = document.getElementById('interaction-button');
    interactText = document.getElementById('interaction-text');
    
    // Make player collide with objects
    this.physics.add.collider(player, interactableObjects);
    
    // Initialize game state from server data
    if (typeof initialGameState !== 'undefined' && initialGameState) {
      loadGameState(initialGameState);
    }
    
    // Setup periodic state saving
    this.time.addEvent({
      delay: 5000,  // Save state every 5 seconds
      callback: saveGameState,
      callbackScope: this,
      loop: true
    });

    // Setup interaction key events
    interactKey.on('down', handleInteraction);
    if (interactButton) {
      interactButton.addEventListener('click', handleInteraction);
    }

  } catch (error) {
    console.error('Error in create function:', error);
    debugText.setText('Error: ' + error.message);
  }
}

// Create classroom objects
function createClassroomObjects(scene) {
  // Create static group for interactable objects
  interactableObjects = scene.physics.add.staticGroup();

  // Remove wall rectangles (do not add them)

  // Add whiteboard
  const whiteboard = interactableObjects.create(config.width / 2, 70, 'whiteboard');
  whiteboard.setScale(0.8);
  whiteboard.refreshBody();
  whiteboard.name = 'whiteboard';
  whiteboard.setDepth(1);

  // Add windows
  const windowSpacing = 200;
  for (let x = windowSpacing; x < config.width - windowSpacing; x += windowSpacing) {
    const window = scene.add.image(x, 40, 'window');
    window.setScale(0.6);
    window.setDepth(0);
  }

  // Add door
  const door = interactableObjects.create(config.width - 60, config.height - 60, 'door');
  door.setScale(0.7);
  door.refreshBody();
  door.name = 'door';
  door.setDepth(1);

  // Add desks and chairs
  const deskRows = 3;
  const desksPerRow = 4;
  const startX = 150;
  const startY = 150;
  const spacingX = 200;
  const spacingY = 150;

  for (let row = 0; row < deskRows; row++) {
    for (let col = 0; col < desksPerRow; col++) {
      const x = startX + col * spacingX;
      const y = startY + row * spacingY;

      // Add desk
      const desk = interactableObjects.create(x, y, 'desk');
      desk.setScale(0.6);
      desk.refreshBody();
      desk.name = `desk-${row}-${col}`;
      desk.setDepth(1);

      // Add chair
      const chair = interactableObjects.create(x, y + 40, 'chair');
      chair.setScale(0.5);
      chair.refreshBody();
      chair.name = `chair-${row}-${col}`;
      chair.chairId = `chair_${row}_${col}`;
      chair.setDepth(1);
      chair.isChair = true;
    }
  }
}

// Create character animations
function createAnimations(scene) {
  // Remove old animations if they exist
  [
    'walk-down', 'walk-left', 'walk-right', 'walk-up',
    'idle-down', 'idle-left', 'idle-right', 'idle-up'
  ].forEach(key => {
    if (scene.anims.exists(key)) scene.anims.remove(key);
  });

  // Walk animations
  scene.anims.create({
    key: 'walk-down',
    frames: scene.anims.generateFrameNumbers(currentCharacterKey, { start: 0, end: 3 }),
    frameRate: 8,
    repeat: -1
  });

  scene.anims.create({
    key: 'walk-left',
    frames: scene.anims.generateFrameNumbers(currentCharacterKey, { start: 4, end: 7 }),
    frameRate: 8,
    repeat: -1
  });

  scene.anims.create({
    key: 'walk-right',
    frames: scene.anims.generateFrameNumbers(currentCharacterKey, { start: 8, end: 11 }),
    frameRate: 8,
    repeat: -1
  });

  scene.anims.create({
    key: 'walk-up',
    frames: scene.anims.generateFrameNumbers(currentCharacterKey, { start: 12, end: 15 }),
    frameRate: 8,
    repeat: -1
  });

  // Idle animations
  scene.anims.create({
    key: 'idle-down',
    frames: [{ key: currentCharacterKey, frame: 0 }],
    frameRate: 1
  });

  scene.anims.create({
    key: 'idle-left',
    frames: [{ key: currentCharacterKey, frame: 4 }],
    frameRate: 1
  });

  scene.anims.create({
    key: 'idle-right',
    frames: [{ key: currentCharacterKey, frame: 8 }],
    frameRate: 1
  });

  scene.anims.create({
    key: 'idle-up',
    frames: [{ key: currentCharacterKey, frame: 12 }],
    frameRate: 1
  });
}

// Update game state
function update() {
  if (!player || !cursors) return;

  // Only handle movement if player is not seated
  if (!isPlayerSeated) {
    handlePlayerMovement();
  }

  // Check for nearby interactable objects
  checkInteractions();

  // Update debug text
  if (debugText) {
    debugText.setText(`X: ${Math.round(player.x)}, Y: ${Math.round(player.y)}\nNear: ${currentInteractable?.name || 'none'}`);
  }
}

// Handle player movement with animations
function handlePlayerMovement() {
  if (!cursors) return;

  const speed = 160;
  let velocityX = 0;
  let velocityY = 0;
  let animation = 'idle';
  let direction = 'down';

  // Get current direction from animation if playing
  if (player.anims && player.anims.isPlaying) {
    direction = player.anims.currentAnim.key.split('-')[1];
  }

  // Check keyboard input
  if (cursors.left?.isDown || cursors.a?.isDown) {
    velocityX = -speed;
    animation = 'walk';
    direction = 'left';
  } else if (cursors.right?.isDown || cursors.d?.isDown) {
    velocityX = speed;
    animation = 'walk';
    direction = 'right';
  }

  if (cursors.up?.isDown || cursors.w?.isDown) {
    velocityY = -speed;
    animation = 'walk';
    direction = 'up';
  } else if (cursors.down?.isDown || cursors.s?.isDown) {
    velocityY = speed;
    animation = 'walk';
    direction = 'down';
  }

  // Normalize diagonal movement
  if (velocityX !== 0 && velocityY !== 0) {
    velocityX *= Math.SQRT1_2;
    velocityY *= Math.SQRT1_2;
  }

  // Apply velocity to player
  player.setVelocity(velocityX, velocityY);

  // Play appropriate animation
  if (animation === 'walk') {
    player.anims.play(`walk-${direction}`, true);
  } else {
    player.anims.play(`idle-${direction}`, true);
  }
}

// Check for interactions with objects
function checkInteractions() {
  if (!player || !interactableObjects) return;

  let foundInteractable = false;
  let closestDistance = 60; // Interaction radius
  let closestObject = null;

  interactableObjects.getChildren().forEach(object => {
    const distance = Phaser.Math.Distance.Between(player.x, player.y, object.x, object.y);
    if (distance < closestDistance) {
      closestDistance = distance;
      closestObject = object;
      foundInteractable = true;
    }
  });

  if (foundInteractable && closestObject !== currentInteractable) {
    currentInteractable = closestObject;
    const interactText = closestObject.isChair ? (isPlayerSeated ? 'Stand' : 'Sit') : 'Interact';
    showInteractionButton(interactText);
  } else if (!foundInteractable && currentInteractable) {
    currentInteractable = null;
    hideInteractionButton();
  }
}

// Handle interaction with objects
function handleInteraction() {
  if (!currentInteractable) return;

  if (currentInteractable.isChair) {
    handleChairInteraction(currentInteractable);
  } else if (currentInteractable.name === 'whiteboard') {
    handleWhiteboardInteraction();
  } else if (currentInteractable.name === 'door') {
    handleDoorInteraction();
  }
}

// Handle chair interaction
function handleChairInteraction(chair) {
  if (isPlayerSeated && chair !== currentChair) {
    // If trying to sit in a different chair while seated, return
    return;
  }

  if (!isPlayerSeated) {
    // Sit down
    player.setVisible(false);
    player.setVelocity(0, 0);
    chair.setTexture('chair-taken');
    isPlayerSeated = true;
    currentChair = chair;
    showInteractionButton('Stand');

    // Update chair occupancy
    chairsOccupancy[chair.chairId] = {
      userId: currentUser.id,
      username: currentUser.username,
      avatar: currentUser.avatar
    };
  } else {
    // Stand up
    player.setVisible(true);
    chair.setTexture('chair');
    isPlayerSeated = false;
    currentChair = null;
    showInteractionButton('Sit');

    // Remove chair occupancy
    delete chairsOccupancy[chair.chairId];
  }

  // Save state and update UI
  saveGameState();
  updateUsersList();
}

// Show interaction button with custom text
function showInteractionButton(text) {
  if (interactButton && interactText) {
    interactButton.classList.remove('hidden');
    interactText.textContent = text;
  }
}

// Hide interaction button
function hideInteractionButton() {
  if (interactButton) {
    interactButton.classList.add('hidden');
  }
}

// Handle whiteboard interaction
function handleWhiteboardInteraction() {
  // TODO: Implement whiteboard functionality
  console.log('Opening whiteboard...');
}

// Handle door interaction
function handleDoorInteraction() {
  // TODO: Implement door functionality
  console.log('Exiting classroom...');
}

// Save game state to server
function saveGameState() {
  if (!player) return;

  const gameState = {
    position: {
      x: player.x,
      y: player.y
    },
    chairsOccupancy: chairsOccupancy
  };

  fetch('/classroom/save-state/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    },
    body: JSON.stringify(gameState)
  }).catch(error => {
    console.error('Error saving game state:', error);
  });
}

// Load game state from server data
function loadGameState(state) {
  if (!player || !state) return;

  if (state.position) {
    player.x = state.position.x;
    player.y = state.position.y;
  }

  if (state.chairsOccupancy) {
    chairsOccupancy = state.chairsOccupancy;
    // Update chair textures based on occupancy
    interactableObjects.getChildren().forEach(object => {
      if (object.isChair && chairsOccupancy[object.chairId]) {
        object.setTexture('chair-taken');
        if (chairsOccupancy[object.chairId].userId === currentUser.id) {
          isPlayerSeated = true;
          currentChair = object;
          player.setVisible(false);
        }
      }
    });
  }

  // Update the UI
  updateUsersList();
}

// Update the list of users in the classroom
function updateUsersList() {
  const usersListElement = document.getElementById('users-list');
  if (!usersListElement) return;
  
  usersListElement.innerHTML = '';
  
  // Get unique users from chair occupancy
  const users = new Map();
  
  for (const chairId in chairsOccupancy) {
    const chairData = chairsOccupancy[chairId];
    if (chairData && chairData.userId) {
      users.set(chairData.userId, chairData);
    }
  }
  
  // Create element for each user
  if (users.size === 0) {
    const emptyElement = document.createElement('p');
    emptyElement.className = 'text-gray-500 dark:text-gray-400';
    emptyElement.textContent = 'No one is seated yet';
    usersListElement.appendChild(emptyElement);
  } else {
    users.forEach(userData => {
      const userElement = document.createElement('div');
      userElement.className = 'flex items-center space-x-2 p-2 bg-gray-50 dark:bg-gray-700 rounded';
      
      // Avatar
      const avatarElement = document.createElement('div');
      if (userData.avatar) {
        avatarElement.className = 'w-8 h-8 rounded-full overflow-hidden';
        const img = document.createElement('img');
        img.src = userData.avatar;
        img.alt = userData.username;
        img.className = 'w-full h-full object-cover';
        avatarElement.appendChild(img);
      } else {
        avatarElement.className = 'w-8 h-8 rounded-full bg-teal-300 flex items-center justify-center text-white font-bold';
        avatarElement.textContent = userData.username.charAt(0).toUpperCase();
      }
      
      // Username
      const usernameElement = document.createElement('span');
      usernameElement.className = 'text-gray-700 dark:text-gray-300';
      usernameElement.textContent = userData.username;
      
      userElement.appendChild(avatarElement);
      userElement.appendChild(usernameElement);
      usersListElement.appendChild(userElement);
    });
  }
}

// Update the DOMContentLoaded event listener
document.addEventListener('DOMContentLoaded', updateUsersList);

function swapCharacter() {
  currentCharacterKey = (currentCharacterKey === 'character') ? 'character-2' : 'character';
  player.setTexture(currentCharacterKey);
  createAnimations(player.scene);
  player.anims.play('idle-down', true);
}

// Attach event listener after DOM is loaded
if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', function() {
    const swapBtn = document.getElementById('swap-character-btn');
    if (swapBtn) {
      swapBtn.addEventListener('click', swapCharacter);
    }
  });
} 