// Flappy Bird Game
class FlappyBird {
    constructor() {
        this.canvas = document.getElementById('gameCanvas');
        this.ctx = this.canvas.getContext('2d');
        
        // Game state
        this.gameState = 'ready'; // ready, playing, gameover
        this.score = 0;
        this.highScore = localStorage.getItem('flappyHighScore') || 0;
        this.updateHighScoreDisplay();
        
        // Bird properties
        this.bird = {
            x: 50,
            y: this.canvas.height / 2,
            radius: 15,
            velocity: 0,
            gravity: 0.5,
            jumpStrength: -10,
            color: '#FFD700'
        };
        
        // Pipes
        this.pipes = [];
        this.pipeWidth = 60;
        this.pipeGap = 150;
        this.pipeSpeed = 3;
        this.pipeFrequency = 100; // frames between pipes
        
        // Game loop
        this.frameCount = 0;
        this.animationId = null;
        
        // Initialize
        this.init();
    }
    
    init() {
        // Set up event listeners
        this.canvas.addEventListener('click', () => this.handleTap());
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' || e.key === ' ') {
                this.handleTap();
            }
        });
        
        // Touch events for mobile
        document.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.handleTap();
        }, { passive: false });
        
        // Button events
        document.getElementById('startBtn').addEventListener('click', () => this.startGame());
        document.getElementById('restartBtn').addEventListener('click', () => this.restartGame());
        document.getElementById('playAgainBtn').addEventListener('click', () => this.restartGame());
        
        // Update score display
        this.updateScoreDisplay();
        
        // Draw initial screen
        this.draw();
    }
    
    handleTap() {
        if (this.gameState === 'playing') {
            this.bird.velocity = this.bird.jumpStrength;
        } else if (this.gameState === 'ready') {
            this.startGame();
        } else if (this.gameState === 'gameover') {
            this.restartGame();
        }
    }
    
    startGame() {
        if (this.gameState === 'playing') return;
        
        this.gameState = 'playing';
        this.score = 0;
        this.frameCount = 0;
        this.pipes = [];
        this.bird.y = this.canvas.height / 2;
        this.bird.velocity = 0;
        
        // Update UI
        document.getElementById('startBtn').style.display = 'none';
        document.getElementById('restartBtn').style.display = 'inline-block';
        document.getElementById('gameOver').style.display = 'none';
        this.updateScoreDisplay();
        
        // Start game loop
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        this.gameLoop();
    }
    
    restartGame() {
        this.gameState = 'ready';
        this.score = 0;
        this.pipes = [];
        this.bird.y = this.canvas.height / 2;
        this.bird.velocity = 0;
        
        // Update UI
        document.getElementById('startBtn').style.display = 'inline-block';
        document.getElementById('restartBtn').style.display = 'none';
        document.getElementById('gameOver').style.display = 'none';
        this.updateScoreDisplay();
        
        // Draw ready screen
        this.draw();
    }
    
    gameLoop() {
        if (this.gameState !== 'playing') return;
        
        this.update();
        this.draw();
        
        if (this.gameState === 'playing') {
            this.animationId = requestAnimationFrame(() => this.gameLoop());
        }
    }
    
    update() {
        // Update bird
        this.bird.velocity += this.bird.gravity;
        this.bird.y += this.bird.velocity;
        
        // Check boundaries
        if (this.bird.y - this.bird.radius <= 0) {
            this.bird.y = this.bird.radius;
            this.bird.velocity = 0;
        }
        
        if (this.bird.y + this.bird.radius >= this.canvas.height) {
            this.gameOver();
            return;
        }
        
        // Generate pipes
        this.frameCount++;
        if (this.frameCount % this.pipeFrequency === 0) {
            this.createPipe();
        }
        
        // Update pipes
        for (let i = this.pipes.length - 1; i >= 0; i--) {
            this.pipes[i].x -= this.pipeSpeed;
            
            // Remove off-screen pipes
            if (this.pipes[i].x + this.pipeWidth < 0) {
                this.pipes.splice(i, 1);
            }
            
            // Check collision
            if (this.checkCollision(this.pipes[i])) {
                this.gameOver();
                return;
            }
            
            // Score point when passing pipe
            if (this.pipes[i].x + this.pipeWidth === Math.floor(this.bird.x - this.pipeSpeed)) {
                this.score++;
                this.updateScoreDisplay();
                
                // Update high score
                if (this.score > this.highScore) {
                    this.highScore = this.score;
                    localStorage.setItem('flappyHighScore', this.highScore);
                    this.updateHighScoreDisplay();
                }
            }
        }
    }
    
    createPipe() {
        const minHeight = 50;
        const maxHeight = this.canvas.height - this.pipeGap - minHeight;
        const topHeight = Math.floor(Math.random() * (maxHeight - minHeight)) + minHeight;
        
        this.pipes.push({
            x: this.canvas.width,
            topHeight: topHeight,
            passed: false
        });
    }
    
    checkCollision(pipe) {
        // Bird collision with pipe
        const birdLeft = this.bird.x - this.bird.radius;
        const birdRight = this.bird.x + this.bird.radius;
        const birdTop = this.bird.y - this.bird.radius;
        const birdBottom = this.bird.y + this.bird.radius;
        
        const pipeRight = pipe.x + this.pipeWidth;
        const pipeLeft = pipe.x;
        
        // Horizontal collision
        if (birdRight > pipeLeft && birdLeft < pipeRight) {
            // Top pipe collision
            if (birdTop < pipe.topHeight) {
                return true;
            }
            // Bottom pipe collision
            if (birdBottom > pipe.topHeight + this.pipeGap) {
                return true;
            }
        }
        
        return false;
    }
    
    gameOver() {
        this.gameState = 'gameover';
        
        // Update final score displays
        document.getElementById('finalScore').textContent = this.score;
        document.getElementById('finalHighScore').textContent = this.highScore;
        document.getElementById('gameOver').style.display = 'flex';
        
        // Cancel animation frame
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }
    
    draw() {
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw sky
        this.ctx.fillStyle = '#87CEEB';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw ground
        this.ctx.fillStyle = '#8B4513';
        this.ctx.fillRect(0, this.canvas.height - 20, this.canvas.width, 20);
        
        // Draw grass
        this.ctx.fillStyle = '#7CFC00';
        this.ctx.fillRect(0, this.canvas.height - 20, this.canvas.width, 5);
        
        // Draw pipes
        this.pipes.forEach(pipe => {
            // Top pipe
            this.ctx.fillStyle = '#228B22';
            this.ctx.fillRect(pipe.x, 0, this.pipeWidth, pipe.topHeight);
            
            // Bottom pipe
            this.ctx.fillRect(
                pipe.x, 
                pipe.topHeight + this.pipeGap, 
                this.pipeWidth, 
                this.canvas.height - (pipe.topHeight + this.pipeGap)
            );
            
            // Pipe caps
            this.ctx.fillStyle = '#32CD32';
            this.ctx.fillRect(pipe.x - 5, pipe.topHeight - 20, this.pipeWidth + 10, 20);
            this.ctx.fillRect(pipe.x - 5, pipe.topHeight + this.pipeGap, this.pipeWidth + 10, 20);
        });
        
        // Draw bird
        this.ctx.fillStyle = this.bird.color;
        this.ctx.beginPath();
        this.ctx.arc(this.bird.x, this.bird.y, this.bird.radius, 0, Math.PI * 2);
        this.ctx.fill();
        
        // Draw eye
        this.ctx.fillStyle = 'black';
        this.ctx.beginPath();
        this.ctx.arc(this.bird.x + 5, this.bird.y - 5, 3, 0, Math.PI * 2);
        this.ctx.fill();
        
        // Draw beak
        this.ctx.fillStyle = '#FF4500';
        this.ctx.beginPath();
        this.ctx.moveTo(this.bird.x + 15, this.bird.y);
        this.ctx.lineTo(this.bird.x + 25, this.bird.y - 5);
        this.ctx.lineTo(this.bird.x + 25, this.bird.y + 5);
        this.ctx.closePath();
        this.ctx.fill();
        
        // Draw game state text
        if (this.gameState === 'ready') {
            this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            this.ctx.font = 'bold 24px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.fillText('Tap to Start!', this.canvas.width / 2, this.canvas.height / 2);
        }
    }
    
    updateScoreDisplay() {
        document.getElementById('score').textContent = this.score;
    }
    
    updateHighScoreDisplay() {
        document.getElementById('highScore').textContent = this.highScore;
    }
}

// Initialize game when page loads
window.addEventListener('DOMContentLoaded', () => {
    const game = new FlappyBird();
    window.flappyGame = game; // Make accessible for debugging
    
    // Update source link
    document.getElementById('sourceLink').href = window.location.href;
});