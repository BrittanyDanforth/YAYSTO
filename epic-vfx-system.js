// ========================================
// EPIC VFX SYSTEM - ABSOLUTELY INSANE EFFECTS
// ========================================

class EpicVFXSystem {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.particles = [];
        this.init();
        this.setupEventListeners();
    }

    init() {
        // Create canvas for particle effects
        this.canvas = document.createElement('canvas');
        this.canvas.id = 'vfx-canvas';
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        document.body.appendChild(this.canvas);
        
        this.ctx = this.canvas.getContext('2d');
        
        // Handle window resize
        window.addEventListener('resize', () => {
            this.canvas.width = window.innerWidth;
            this.canvas.height = window.innerHeight;
        });
        
        // Start animation loop
        this.animate();
    }

    setupEventListeners() {
        // Listen for 'E' key press on interactive elements
        document.addEventListener('keydown', (e) => {
            if (e.key === 'e' || e.key === 'E') {
                // Get all interactive elements
                const interactives = document.querySelectorAll('.interactive-element, .choice, .control-button');
                
                // Find the hovered or focused element
                interactives.forEach(el => {
                    if (el.matches(':hover') || document.activeElement === el) {
                        const rect = el.getBoundingClientRect();
                        const x = rect.left + rect.width / 2;
                        const y = rect.top + rect.height / 2;
                        
                        this.triggerEpicVFX(x, y);
                    }
                });
            }
        });

        // Also trigger on click for any interactive element
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('interactive-element') || 
                e.target.classList.contains('choice') ||
                e.target.classList.contains('control-button')) {
                this.triggerEpicVFX(e.clientX, e.clientY);
            }
        });
    }

    triggerEpicVFX(x, y) {
        console.log('🔥 EPIC VFX TRIGGERED! 🔥');
        
        // Screen shake
        document.body.classList.add('screen-shake');
        setTimeout(() => document.body.classList.remove('screen-shake'), 500);
        
        // Radial burst
        this.createRadialBurst(x, y);
        
        // Star sparkles
        this.createStarSparkles(x, y);
        
        // Energy rays
        this.createEnergyRays(x, y);
        
        // Hexagon effect
        this.createHexagonEffect(x, y);
        
        // Color flash
        this.createColorFlash();
        
        // Circular waves
        this.createCircularWaves(x, y);
        
        // Text popup
        this.createTextPopup(x, y);
        
        // Lightning effect
        this.createLightningEffect();
        
        // Vortex effect
        this.createVortexEffect(x, y);
        
        // Canvas particles
        this.createParticleExplosion(x, y);
        
        // Chromatic aberration
        document.body.classList.add('chromatic-effect');
        setTimeout(() => document.body.classList.remove('chromatic-effect'), 600);
        
        // Play sound effect (if available)
        this.playVFXSound();
    }

    createRadialBurst(x, y) {
        const burst = document.createElement('div');
        burst.className = 'radial-burst';
        burst.style.left = `${x - 200}px`;
        burst.style.top = `${y - 200}px`;
        document.body.appendChild(burst);
        
        setTimeout(() => burst.remove(), 1000);
    }

    createStarSparkles(x, y) {
        const sparkleCount = 20;
        
        for (let i = 0; i < sparkleCount; i++) {
            setTimeout(() => {
                const sparkle = document.createElement('div');
                sparkle.className = 'star-sparkle';
                
                const angle = (Math.PI * 2 * i) / sparkleCount;
                const distance = 50 + Math.random() * 100;
                const offsetX = Math.cos(angle) * distance;
                const offsetY = Math.sin(angle) * distance;
                
                sparkle.style.left = `${x + offsetX}px`;
                sparkle.style.top = `${y + offsetY}px`;
                
                // Random size
                const size = 15 + Math.random() * 15;
                sparkle.style.width = `${size}px`;
                sparkle.style.height = `${size}px`;
                
                document.body.appendChild(sparkle);
                
                setTimeout(() => sparkle.remove(), 1000);
            }, i * 30);
        }
    }

    createEnergyRays(x, y) {
        const rayCount = 12;
        
        for (let i = 0; i < rayCount; i++) {
            const ray = document.createElement('div');
            ray.className = 'energy-ray';
            
            const angle = (Math.PI * 2 * i) / rayCount;
            const length = 200 + Math.random() * 200;
            
            ray.style.left = `${x}px`;
            ray.style.top = `${y}px`;
            ray.style.width = `${length}px`;
            ray.style.transform = `rotate(${angle}rad)`;
            
            // Random colors
            const colors = ['#00ffff', '#ff00ff', '#ffff00', '#00ff00'];
            const color = colors[Math.floor(Math.random() * colors.length)];
            ray.style.background = `linear-gradient(90deg, ${color}, transparent)`;
            ray.style.boxShadow = `0 0 10px ${color}`;
            
            document.body.appendChild(ray);
            
            setTimeout(() => ray.remove(), 600);
        }
    }

    createHexagonEffect(x, y) {
        const hexagon = document.createElement('div');
        hexagon.className = 'hexagon-effect';
        hexagon.style.left = `${x}px`;
        hexagon.style.top = `${y}px`;
        document.body.appendChild(hexagon);
        
        setTimeout(() => hexagon.remove(), 1200);
    }

    createColorFlash() {
        const flash = document.createElement('div');
        flash.className = 'color-flash';
        
        // Random color
        const colors = [
            'radial-gradient(circle, rgba(0, 255, 255, 0.3) 0%, transparent 70%)',
            'radial-gradient(circle, rgba(255, 0, 255, 0.3) 0%, transparent 70%)',
            'radial-gradient(circle, rgba(138, 43, 226, 0.3) 0%, transparent 70%)'
        ];
        flash.style.background = colors[Math.floor(Math.random() * colors.length)];
        
        document.body.appendChild(flash);
        
        setTimeout(() => flash.remove(), 400);
    }

    createCircularWaves(x, y) {
        const waveCount = 3;
        
        for (let i = 0; i < waveCount; i++) {
            setTimeout(() => {
                const wave = document.createElement('div');
                wave.className = 'circular-wave';
                wave.style.left = `${x}px`;
                wave.style.top = `${y}px`;
                
                // Different colors for each wave
                const colors = ['#00ffff', '#ff00ff', '#ffff00'];
                wave.style.borderColor = colors[i % colors.length];
                wave.style.boxShadow = `0 0 30px ${colors[i % colors.length]}`;
                
                document.body.appendChild(wave);
                
                setTimeout(() => wave.remove(), 1000);
            }, i * 200);
        }
    }

    createTextPopup(x, y) {
        const texts = ['EPIC!', 'LEGENDARY!', 'INSANE!', 'WOW!', 'BOOM!', 'AMAZING!', 'SPECTACULAR!'];
        const text = texts[Math.floor(Math.random() * texts.length)];
        
        const popup = document.createElement('div');
        popup.className = 'text-popup';
        popup.textContent = text;
        popup.style.left = `${x}px`;
        popup.style.top = `${y}px`;
        document.body.appendChild(popup);
        
        setTimeout(() => popup.remove(), 1500);
    }

    createLightningEffect() {
        const lightning = document.createElement('div');
        lightning.className = 'lightning-effect';
        document.body.appendChild(lightning);
        
        setTimeout(() => lightning.remove(), 300);
    }

    createVortexEffect(x, y) {
        const vortex = document.createElement('div');
        vortex.className = 'vortex-effect';
        vortex.style.left = `${x}px`;
        vortex.style.top = `${y}px`;
        document.body.appendChild(vortex);
        
        setTimeout(() => vortex.remove(), 1500);
    }

    createParticleExplosion(x, y) {
        const particleCount = 150;
        
        for (let i = 0; i < particleCount; i++) {
            const angle = Math.random() * Math.PI * 2;
            const velocity = 2 + Math.random() * 8;
            const lifetime = 30 + Math.random() * 60;
            const size = 2 + Math.random() * 6;
            
            // Random color with more variety
            const colors = [
                { r: 0, g: 255, b: 255 },    // Cyan
                { r: 255, g: 0, b: 255 },    // Magenta
                { r: 138, g: 43, b: 226 },   // Purple
                { r: 255, g: 255, b: 0 },    // Yellow
                { r: 0, g: 255, b: 0 },      // Green
                { r: 255, g: 107, b: 53 }    // Brand orange
            ];
            const color = colors[Math.floor(Math.random() * colors.length)];
            
            this.particles.push({
                x: x,
                y: y,
                vx: Math.cos(angle) * velocity,
                vy: Math.sin(angle) * velocity,
                life: lifetime,
                maxLife: lifetime,
                size: size,
                color: color,
                glow: true
            });
        }
    }

    animate() {
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Update and draw particles
        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];
            
            // Update position
            p.x += p.vx;
            p.y += p.vy;
            
            // Apply gravity
            p.vy += 0.15;
            
            // Apply friction
            p.vx *= 0.98;
            p.vy *= 0.98;
            
            // Decrease life
            p.life--;
            
            // Remove dead particles
            if (p.life <= 0) {
                this.particles.splice(i, 1);
                continue;
            }
            
            // Calculate alpha based on life
            const alpha = p.life / p.maxLife;
            
            // Draw particle
            this.ctx.save();
            
            if (p.glow) {
                // Add glow effect
                this.ctx.shadowBlur = 15;
                this.ctx.shadowColor = `rgba(${p.color.r}, ${p.color.g}, ${p.color.b}, ${alpha})`;
            }
            
            this.ctx.fillStyle = `rgba(${p.color.r}, ${p.color.g}, ${p.color.b}, ${alpha})`;
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            this.ctx.fill();
            
            this.ctx.restore();
            
            // Draw particle trail
            if (p.glow) {
                this.ctx.save();
                this.ctx.strokeStyle = `rgba(${p.color.r}, ${p.color.g}, ${p.color.b}, ${alpha * 0.3})`;
                this.ctx.lineWidth = p.size * 0.5;
                this.ctx.beginPath();
                this.ctx.moveTo(p.x, p.y);
                this.ctx.lineTo(p.x - p.vx * 2, p.y - p.vy * 2);
                this.ctx.stroke();
                this.ctx.restore();
            }
        }
        
        requestAnimationFrame(() => this.animate());
    }

    playVFXSound() {
        // Create a simple sound effect using Web Audio API
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            // Create oscillators for a complex sound
            const oscillator1 = audioContext.createOscillator();
            const oscillator2 = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator1.connect(gainNode);
            oscillator2.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator1.type = 'sine';
            oscillator2.type = 'square';
            
            oscillator1.frequency.setValueAtTime(440, audioContext.currentTime);
            oscillator2.frequency.setValueAtTime(880, audioContext.currentTime);
            
            // Envelope
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
            
            oscillator1.start(audioContext.currentTime);
            oscillator2.start(audioContext.currentTime);
            oscillator1.stop(audioContext.currentTime + 0.3);
            oscillator2.stop(audioContext.currentTime + 0.3);
        } catch (e) {
            console.log('Audio not supported');
        }
    }

    // Method to manually trigger VFX (can be called from external code)
    trigger(x = window.innerWidth / 2, y = window.innerHeight / 2) {
        this.triggerEpicVFX(x, y);
    }
}

// Initialize the VFX system when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.epicVFX = new EpicVFXSystem();
        console.log('🎆 Epic VFX System Initialized! Press E on any interactive element! 🎆');
    });
} else {
    window.epicVFX = new EpicVFXSystem();
    console.log('🎆 Epic VFX System Initialized! Press E on any interactive element! 🎆');
}

// Make all choice buttons and control buttons interactive
document.addEventListener('DOMContentLoaded', () => {
    // Add interactive class to all choices
    const choices = document.querySelectorAll('.choice');
    choices.forEach(choice => {
        if (!choice.classList.contains('interactive-element')) {
            choice.classList.add('interactive-element');
        }
    });
    
    // Add interactive class to all control buttons
    const buttons = document.querySelectorAll('.control-button, .primary-button, .secondary-button');
    buttons.forEach(button => {
        if (!button.classList.contains('interactive-element')) {
            button.classList.add('interactive-element');
        }
    });
    
    // Add some demo interactive elements to the page
    console.log('✨ Interactive elements ready! Hover over choices and press E! ✨');
});

// Expose a global function to trigger VFX from console or other scripts
window.triggerEpicVFX = (x, y) => {
    if (window.epicVFX) {
        window.epicVFX.trigger(x, y);
    }
};
