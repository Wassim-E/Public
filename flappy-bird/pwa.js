// Progressive Web App functionality
class PWAInstaller {
    constructor() {
        this.deferredPrompt = null;
        this.installButton = document.getElementById('installBtn');
        this.isStandalone = window.matchMedia('(display-mode: standalone)').matches || 
                           window.navigator.standalone === true;
        
        this.init();
    }
    
    init() {
        // Check if already installed
        if (this.isStandalone) {
            console.log('App is running in standalone mode');
            this.installButton.style.display = 'none';
            return;
        }
        
        // Listen for beforeinstallprompt event
        window.addEventListener('beforeinstallprompt', (e) => {
            console.log('beforeinstallprompt event fired');
            e.preventDefault();
            this.deferredPrompt = e;
            
            // Show install button
            this.installButton.style.display = 'inline-block';
            
            // Update button text based on platform
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
            if (isIOS) {
                this.installButton.innerHTML = '📱 Install (iOS)';
                this.installButton.title = 'Tap share button, then "Add to Home Screen"';
            }
        });
        
        // Listen for appinstalled event
        window.addEventListener('appinstalled', () => {
            console.log('PWA was installed');
            this.installButton.style.display = 'none';
            this.deferredPrompt = null;
            
            // Show success message
            this.showToast('App installed successfully! 🎉');
        });
        
        // Install button click handler
        this.installButton.addEventListener('click', () => this.installApp());
        
        // Check if app is already installed
        this.checkIfInstalled();
    }
    
    async installApp() {
        if (!this.deferredPrompt) {
            // For iOS or browsers that don't support beforeinstallprompt
            this.showInstallInstructions();
            return;
        }
        
        // Show the install prompt
        this.deferredPrompt.prompt();
        
        // Wait for the user to respond to the prompt
        const { outcome } = await this.deferredPrompt.userChoice;
        
        if (outcome === 'accepted') {
            console.log('User accepted the install prompt');
            this.installButton.style.display = 'none';
        } else {
            console.log('User dismissed the install prompt');
        }
        
        // Clear the saved prompt since it can't be used again
        this.deferredPrompt = null;
    }
    
    showInstallInstructions() {
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
        const isAndroid = /Android/.test(navigator.userAgent);
        
        let message = '';
        
        if (isIOS) {
            message = 'To install this app:\n1. Tap the share button (📤)\n2. Scroll down and tap "Add to Home Screen"\n3. Tap "Add" in the top right';
        } else if (isAndroid) {
            message = 'To install this app:\n1. Tap the menu button (⋮)\n2. Tap "Install App" or "Add to Home Screen"';
        } else {
            message = 'Look for the install icon in your browser\'s address bar or menu';
        }
        
        alert(message);
    }
    
    checkIfInstalled() {
        // Check various indicators
        if (window.matchMedia('(display-mode: standalone)').matches) {
            this.installButton.style.display = 'none';
            return true;
        }
        
        if (window.navigator.standalone) {
            this.installButton.style.display = 'none';
            return true;
        }
        
        // Check for presence of service worker
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.getRegistration()
                .then(registration => {
                    if (registration) {
                        console.log('Service worker registered');
                    }
                });
        }
        
        return false;
    }
    
    showToast(message) {
        // Create toast element
        const toast = document.createElement('div');
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            z-index: 1000;
            font-weight: bold;
            animation: fadeInOut 3s ease-in-out;
        `;
        
        // Add animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes fadeInOut {
                0% { opacity: 0; transform: translateX(-50%) translateY(20px); }
                15% { opacity: 1; transform: translateX(-50%) translateY(0); }
                85% { opacity: 1; transform: translateX(-50%) translateY(0); }
                100% { opacity: 0; transform: translateX(-50%) translateY(-20px); }
            }
        `;
        document.head.appendChild(style);
        
        document.body.appendChild(toast);
        
        // Remove after animation
        setTimeout(() => {
            document.body.removeChild(toast);
            document.head.removeChild(style);
        }, 3000);
    }
}

// Register service worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/flappy-bird/sw.js')
            .then(registration => {
                console.log('ServiceWorker registration successful:', registration.scope);
            })
            .catch(error => {
                console.log('ServiceWorker registration failed:', error);
            });
    });
}

// Initialize PWA when page loads
window.addEventListener('DOMContentLoaded', () => {
    const pwa = new PWAInstaller();
    window.pwaInstaller = pwa; // Make accessible for debugging
    
    // Add meta tag for iOS status bar
    const meta = document.createElement('meta');
    meta.name = 'apple-mobile-web-app-status-bar-style';
    meta.content = 'black-translucent';
    document.head.appendChild(meta);
    
    // Prevent bounce on iOS
    document.addEventListener('touchmove', (e) => {
        if (e.scale !== 1) {
            e.preventDefault();
        }
    }, { passive: false });
});