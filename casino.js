// ==========================================
// GLOBAL STATE & UTILITIES
// ==========================================

let balance = 10000;
const RTP = 0.98;

// Secure RNG
function getRandomFloat() {
    const array = new Uint32Array(1);
    crypto.getRandomValues(array);
    return array[0] / (0xFFFFFFFF + 1);
}

function updateBalance(amount) {
    balance += amount;
    document.getElementById('balance').textContent = balance.toFixed(2);
    
    // Animate balance change
    const balanceEl = document.getElementById('balance');
    balanceEl.style.transform = 'scale(1.1)';
    setTimeout(() => {
        balanceEl.style.transform = 'scale(1)';
    }, 200);
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function addHistoryItem(gameId, content, isWin) {
    const historyList = document.getElementById(`${gameId}-history`);
    const item = document.createElement('div');
    item.className = `history-item ${isWin ? 'win' : 'loss'}`;
    item.innerHTML = content;
    historyList.insertBefore(item, historyList.firstChild);
    
    // Keep only last 10 items
    while (historyList.children.length > 10) {
        historyList.removeChild(historyList.lastChild);
    }
}

// ==========================================
// NAVIGATION
// ==========================================

document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
        // Update nav buttons
        document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // Update game sections
        const gameId = btn.dataset.game;
        document.querySelectorAll('.game-section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(`${gameId}-game`).classList.add('active');
    });
});

// ==========================================
// LIMBO GAME
// ==========================================

const limboState = {
    isPlaying: false
};

document.getElementById('limbo-play').addEventListener('click', async () => {
    if (limboState.isPlaying) return;
    
    const betAmount = parseFloat(document.getElementById('limbo-bet').value);
    const targetMultiplier = parseFloat(document.getElementById('limbo-target').value);
    
    // Validation
    if (betAmount < 1 || betAmount > balance) {
        showToast('Invalid bet amount!', 'error');
        return;
    }
    
    if (targetMultiplier < 1.01) {
        showToast('Target multiplier must be at least 1.01x', 'error');
        return;
    }
    
    limboState.isPlaying = true;
    updateBalance(-betAmount);
    
    // Generate crash point using RNG
    const randomNumber = getRandomFloat();
    const crashPoint = Math.max(1.00, RTP / randomNumber);
    
    // UI elements
    const multiplierEl = document.getElementById('limbo-multiplier');
    const valueEl = multiplierEl.querySelector('.multiplier-value');
    const statusEl = document.getElementById('limbo-status');
    const playBtn = document.getElementById('limbo-play');
    
    playBtn.disabled = true;
    statusEl.textContent = '';
    valueEl.classList.remove('winning', 'losing');
    
    // Animate multiplier rising
    let currentMultiplier = 1.00;
    const duration = 2000; // 2 seconds
    const steps = 50;
    const increment = (crashPoint - 1) / steps;
    const stepTime = duration / steps;
    
    for (let i = 0; i <= steps; i++) {
        await new Promise(resolve => setTimeout(resolve, stepTime));
        currentMultiplier = Math.min(1.00 + (increment * i), crashPoint);
        valueEl.textContent = currentMultiplier.toFixed(2) + 'x';
    }
    
    // Final result
    valueEl.textContent = crashPoint.toFixed(2) + 'x';
    
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Check win/loss
    if (crashPoint >= targetMultiplier) {
        const winAmount = betAmount * targetMultiplier;
        updateBalance(winAmount);
        valueEl.classList.add('winning');
        statusEl.textContent = `🎉 YOU WIN ${winAmount.toFixed(2)} COINS!`;
        statusEl.style.color = '#00b894';
        showToast(`Won ${winAmount.toFixed(2)} coins!`, 'success');
        
        addHistoryItem('limbo', `
            <div><strong>${crashPoint.toFixed(2)}x</strong></div>
            <div style="color: #00b894;">+${winAmount.toFixed(2)}</div>
        `, true);
    } else {
        valueEl.classList.add('losing');
        statusEl.textContent = `💥 CRASH! Target: ${targetMultiplier.toFixed(2)}x`;
        statusEl.style.color = '#ff7675';
        showToast(`Lost ${betAmount.toFixed(2)} coins`, 'error');
        
        addHistoryItem('limbo', `
            <div><strong>${crashPoint.toFixed(2)}x</strong></div>
            <div style="color: #ff7675;">-${betAmount.toFixed(2)}</div>
        `, false);
    }
    
    playBtn.disabled = false;
    limboState.isPlaying = false;
});

// ==========================================
// MINES GAME
// ==========================================

const minesState = {
    isPlaying: false,
    minePositions: [],
    revealedTiles: 0,
    currentBet: 0,
    totalTiles: 25,
    mineCount: 3
};

function calculateMinesMultiplier(revealed, mines) {
    const safe = minesState.totalTiles - mines;
    if (revealed === 0) return 1.00;
    
    // Probability of surviving k picks
    let probability = 1;
    for (let i = 0; i < revealed; i++) {
        probability *= (safe - i) / (minesState.totalTiles - i);
    }
    
    // Multiplier with RTP
    return RTP / probability;
}

function createMinesGrid() {
    const grid = document.getElementById('mines-grid');
    grid.innerHTML = '';
    
    for (let i = 0; i < minesState.totalTiles; i++) {
        const tile = document.createElement('div');
        tile.className = 'mine-tile';
        tile.dataset.index = i;
        tile.addEventListener('click', () => handleTileClick(i));
        grid.appendChild(tile);
    }
}

function handleTileClick(index) {
    if (!minesState.isPlaying) return;
    
    const tile = document.querySelector(`[data-index="${index}"]`);
    if (tile.classList.contains('revealed')) return;
    
    tile.classList.add('revealed');
    
    if (minesState.minePositions.includes(index)) {
        // Hit a mine!
        tile.classList.add('mine');
        tile.textContent = '💣';
        endMinesGame(false);
    } else {
        // Safe tile!
        tile.classList.add('gem');
        tile.textContent = '💎';
        minesState.revealedTiles++;
        
        const multiplier = calculateMinesMultiplier(minesState.revealedTiles, minesState.mineCount);
        document.getElementById('mines-multiplier').textContent = multiplier.toFixed(2) + 'x';
        
        const profit = minesState.currentBet * multiplier - minesState.currentBet;
        document.getElementById('mines-profit').textContent = profit.toFixed(2);
        
        document.getElementById('mines-cashout').disabled = false;
    }
}

function endMinesGame(cashedOut) {
    minesState.isPlaying = false;
    
    // Reveal all mines
    minesState.minePositions.forEach(pos => {
        const tile = document.querySelector(`[data-index="${pos}"]`);
        if (!tile.classList.contains('revealed')) {
            tile.classList.add('revealed', 'mine');
            tile.textContent = '💣';
        }
    });
    
    document.getElementById('mines-cashout').disabled = true;
    document.getElementById('mines-start').disabled = false;
    document.getElementById('mines-bet').disabled = false;
    document.getElementById('mines-count').disabled = false;
    
    if (cashedOut) {
        const multiplier = calculateMinesMultiplier(minesState.revealedTiles, minesState.mineCount);
        const winAmount = minesState.currentBet * multiplier;
        updateBalance(winAmount);
        showToast(`Cashed out ${winAmount.toFixed(2)} coins!`, 'success');
        
        addHistoryItem('mines', `
            <div><strong>${minesState.revealedTiles} gems</strong></div>
            <div style="color: #00b894;">+${(winAmount - minesState.currentBet).toFixed(2)}</div>
        `, true);
    } else {
        showToast(`Hit a mine! Lost ${minesState.currentBet.toFixed(2)} coins`, 'error');
        
        addHistoryItem('mines', `
            <div><strong>${minesState.revealedTiles} gems</strong></div>
            <div style="color: #ff7675;">-${minesState.currentBet.toFixed(2)}</div>
        `, false);
    }
    
    setTimeout(() => {
        document.getElementById('mines-multiplier').textContent = '1.00x';
        document.getElementById('mines-profit').textContent = '0.00';
    }, 2000);
}

document.getElementById('mines-start').addEventListener('click', () => {
    const betAmount = parseFloat(document.getElementById('mines-bet').value);
    const mineCount = parseInt(document.getElementById('mines-count').value);
    
    if (betAmount < 1 || betAmount > balance) {
        showToast('Invalid bet amount!', 'error');
        return;
    }
    
    if (mineCount < 1 || mineCount > 24) {
        showToast('Mines must be between 1 and 24!', 'error');
        return;
    }
    
    updateBalance(-betAmount);
    
    minesState.isPlaying = true;
    minesState.currentBet = betAmount;
    minesState.mineCount = mineCount;
    minesState.revealedTiles = 0;
    
    // Generate random mine positions
    minesState.minePositions = [];
    while (minesState.minePositions.length < mineCount) {
        const pos = Math.floor(getRandomFloat() * minesState.totalTiles);
        if (!minesState.minePositions.includes(pos)) {
            minesState.minePositions.push(pos);
        }
    }
    
    createMinesGrid();
    
    document.getElementById('mines-start').disabled = true;
    document.getElementById('mines-bet').disabled = true;
    document.getElementById('mines-count').disabled = true;
    document.getElementById('mines-multiplier').textContent = '1.00x';
    document.getElementById('mines-profit').textContent = '0.00';
});

document.getElementById('mines-cashout').addEventListener('click', () => {
    if (minesState.isPlaying) {
        endMinesGame(true);
    }
});

// Initialize grid
createMinesGrid();

// ==========================================
// CASES GAME
// ==========================================

const casesData = {
    bronze: {
        price: 50,
        items: [
            { name: 'Common Coin', value: 10, rarity: 'common', icon: '🪙', probability: 0.50 },
            { name: 'Silver Coin', value: 30, rarity: 'common', icon: '💿', probability: 0.30 },
            { name: 'Gold Nugget', value: 80, rarity: 'rare', icon: '⚜️', probability: 0.15 },
            { name: 'Ruby Gem', value: 200, rarity: 'epic', icon: '💍', probability: 0.04 },
            { name: 'Diamond', value: 500, rarity: 'legendary', icon: '💎', probability: 0.01 }
        ]
    },
    silver: {
        price: 150,
        items: [
            { name: 'Bronze Bar', value: 50, rarity: 'common', icon: '🥉', probability: 0.45 },
            { name: 'Silver Bar', value: 120, rarity: 'rare', icon: '🥈', probability: 0.35 },
            { name: 'Gold Bar', value: 300, rarity: 'epic', icon: '🥇', probability: 0.15 },
            { name: 'Platinum Bar', value: 700, rarity: 'legendary', icon: '🏆', probability: 0.04 },
            { name: 'Rare Artifact', value: 2000, rarity: 'legendary', icon: '👑', probability: 0.01 }
        ]
    },
    gold: {
        price: 500,
        items: [
            { name: 'Emerald', value: 200, rarity: 'rare', icon: '🟢', probability: 0.40 },
            { name: 'Sapphire', value: 450, rarity: 'rare', icon: '🔵', probability: 0.30 },
            { name: 'Ruby', value: 800, rarity: 'epic', icon: '🔴', probability: 0.20 },
            { name: 'Black Pearl', value: 2000, rarity: 'legendary', icon: '⚫', probability: 0.08 },
            { name: 'Ancient Relic', value: 5000, rarity: 'legendary', icon: '🗿', probability: 0.02 }
        ]
    },
    diamond: {
        price: 1500,
        items: [
            { name: 'Crystal Shard', value: 700, rarity: 'rare', icon: '🔷', probability: 0.35 },
            { name: 'Mystic Orb', value: 1400, rarity: 'epic', icon: '🔮', probability: 0.30 },
            { name: 'Dragon Egg', value: 3000, rarity: 'epic', icon: '🥚', probability: 0.20 },
            { name: 'Phoenix Feather', value: 6000, rarity: 'legendary', icon: '🪶', probability: 0.10 },
            { name: 'Cosmic Gem', value: 15000, rarity: 'legendary', icon: '✨', probability: 0.05 }
        ]
    }
};

function selectCaseItem(caseType) {
    const caseItems = casesData[caseType].items;
    const random = getRandomFloat();
    
    let cumulative = 0;
    for (const item of caseItems) {
        cumulative += item.probability;
        if (random <= cumulative) {
            return item;
        }
    }
    
    return caseItems[caseItems.length - 1];
}

async function openCase(caseType) {
    const casePrice = casesData[caseType].price;
    
    if (balance < casePrice) {
        showToast('Insufficient balance!', 'error');
        return;
    }
    
    updateBalance(-casePrice);
    
    const modal = document.getElementById('case-opening-modal');
    const spinner = document.getElementById('case-spinner');
    const resultDiv = document.getElementById('case-result');
    
    modal.classList.add('active');
    spinner.innerHTML = '';
    resultDiv.innerHTML = '';
    
    // Generate items for spinner (including the winning item)
    const wonItem = selectCaseItem(caseType);
    const allItems = casesData[caseType].items;
    const spinnerItems = [];
    
    // Add random items
    for (let i = 0; i < 20; i++) {
        const randomItem = allItems[Math.floor(getRandomFloat() * allItems.length)];
        spinnerItems.push(randomItem);
    }
    
    // Insert winning item in the middle
    spinnerItems[10] = wonItem;
    
    // Create spinner items
    spinnerItems.forEach(item => {
        const itemEl = document.createElement('div');
        itemEl.className = `case-item ${item.rarity}`;
        itemEl.innerHTML = `
            <div class="case-item-icon">${item.icon}</div>
            <div class="case-item-name">${item.name}</div>
            <div class="case-item-value">${item.value}</div>
        `;
        spinner.appendChild(itemEl);
    });
    
    // Animate spinner
    spinner.style.display = 'flex';
    spinner.style.transition = 'transform 3s cubic-bezier(0.17, 0.67, 0.12, 0.99)';
    spinner.style.transform = 'translateX(0)';
    
    await new Promise(resolve => setTimeout(resolve, 100));
    
    const itemWidth = 130; // 120px + 10px margin
    const targetPosition = -(10 * itemWidth) + (window.innerWidth * 0.4);
    spinner.style.transform = `translateX(${targetPosition}px)`;
    
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Show result
    spinner.style.display = 'none';
    resultDiv.innerHTML = `
        <div class="case-result-item">
            <div class="case-result-icon">${wonItem.icon}</div>
            <div class="case-result-name">${wonItem.name}</div>
            <div class="case-result-value">+${wonItem.value} coins</div>
        </div>
        <button class="btn-primary case-result-close" onclick="closeCaseModal()">Claim Prize</button>
    `;
    
    updateBalance(wonItem.value);
    
    const profit = wonItem.value - casePrice;
    const isWin = profit > 0;
    
    addHistoryItem('cases', `
        <div><strong>${wonItem.name}</strong></div>
        <div style="color: ${isWin ? '#00b894' : '#ff7675'};">${isWin ? '+' : ''}${profit.toFixed(2)}</div>
    `, isWin);
}

function closeCaseModal() {
    document.getElementById('case-opening-modal').classList.remove('active');
}

// Add click handlers to case buttons
document.querySelectorAll('.case-open').forEach(btn => {
    btn.addEventListener('click', () => {
        const caseType = btn.dataset.case;
        openCase(caseType);
    });
});

// ==========================================
// BLACKJACK GAME
// ==========================================

const blackjackState = {
    deck: [],
    playerHand: [],
    dealerHand: [],
    currentBet: 0,
    isPlaying: false,
    playerStood: false
};

const suits = ['♠', '♣', '♥', '♦'];
const ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];

function createDeck() {
    const deck = [];
    // Use 6 decks
    for (let d = 0; d < 6; d++) {
        for (const suit of suits) {
            for (const rank of ranks) {
                deck.push({ rank, suit });
            }
        }
    }
    return deck;
}

function shuffleDeck(deck) {
    for (let i = deck.length - 1; i > 0; i--) {
        const j = Math.floor(getRandomFloat() * (i + 1));
        [deck[i], deck[j]] = [deck[j], deck[i]];
    }
    return deck;
}

function getCardValue(card, currentTotal = 0) {
    if (card.rank === 'A') {
        return (currentTotal + 11 <= 21) ? 11 : 1;
    } else if (['J', 'Q', 'K'].includes(card.rank)) {
        return 10;
    }
    return parseInt(card.rank);
}

function calculateHandValue(hand) {
    let total = 0;
    let aces = 0;
    
    for (const card of hand) {
        if (card.rank === 'A') {
            aces++;
            total += 11;
        } else if (['J', 'Q', 'K'].includes(card.rank)) {
            total += 10;
        } else {
            total += parseInt(card.rank);
        }
    }
    
    while (total > 21 && aces > 0) {
        total -= 10;
        aces--;
    }
    
    return total;
}

function displayCard(card, hidden = false) {
    const isRed = ['♥', '♦'].includes(card.suit);
    
    if (hidden) {
        return `<div class="card back">🂠</div>`;
    }
    
    return `<div class="card ${isRed ? 'red' : 'black'}">${card.rank}${card.suit}</div>`;
}

function updateBlackjackDisplay() {
    const playerHandEl = document.getElementById('player-hand');
    const dealerHandEl = document.getElementById('dealer-hand');
    
    // Display player hand
    playerHandEl.innerHTML = blackjackState.playerHand.map(card => displayCard(card)).join('');
    const playerTotal = calculateHandValue(blackjackState.playerHand);
    document.getElementById('player-total').textContent = `(${playerTotal})`;
    
    // Display dealer hand
    if (blackjackState.playerStood || playerTotal > 21) {
        // Show all dealer cards
        dealerHandEl.innerHTML = blackjackState.dealerHand.map(card => displayCard(card)).join('');
        const dealerTotal = calculateHandValue(blackjackState.dealerHand);
        document.getElementById('dealer-total').textContent = `(${dealerTotal})`;
    } else {
        // Hide dealer's second card
        dealerHandEl.innerHTML = displayCard(blackjackState.dealerHand[0]);
        if (blackjackState.dealerHand.length > 1) {
            dealerHandEl.innerHTML += displayCard(blackjackState.dealerHand[1], true);
        }
        document.getElementById('dealer-total').textContent = '';
    }
}

async function dealerPlay() {
    blackjackState.playerStood = true;
    updateBlackjackDisplay();
    
    await new Promise(resolve => setTimeout(resolve, 500));
    
    while (calculateHandValue(blackjackState.dealerHand) < 17) {
        const card = blackjackState.deck.pop();
        blackjackState.dealerHand.push(card);
        updateBlackjackDisplay();
        await new Promise(resolve => setTimeout(resolve, 600));
    }
    
    endBlackjackRound();
}

function endBlackjackRound() {
    const playerTotal = calculateHandValue(blackjackState.playerHand);
    const dealerTotal = calculateHandValue(blackjackState.dealerHand);
    const statusEl = document.getElementById('bj-status');
    
    let result = '';
    let winAmount = 0;
    let isWin = false;
    
    if (playerTotal > 21) {
        result = '💥 BUST! Dealer wins.';
        statusEl.style.color = '#ff7675';
    } else if (dealerTotal > 21) {
        result = '🎉 Dealer busts! You win!';
        winAmount = blackjackState.currentBet * 2;
        isWin = true;
        statusEl.style.color = '#00b894';
    } else if (playerTotal > dealerTotal) {
        // Check for natural blackjack (pays 3:2)
        if (blackjackState.playerHand.length === 2 && playerTotal === 21) {
            result = '🃏 BLACKJACK! You win 3:2!';
            winAmount = blackjackState.currentBet * 2.5;
        } else {
            result = '🎉 You win!';
            winAmount = blackjackState.currentBet * 2;
        }
        isWin = true;
        statusEl.style.color = '#00b894';
    } else if (playerTotal < dealerTotal) {
        result = '😞 Dealer wins.';
        statusEl.style.color = '#ff7675';
    } else {
        result = '🤝 Push! Bet returned.';
        winAmount = blackjackState.currentBet;
        statusEl.style.color = '#fdcb6e';
    }
    
    statusEl.textContent = result;
    
    if (winAmount > 0) {
        updateBalance(winAmount);
        showToast(result, isWin ? 'success' : 'info');
    } else {
        showToast(result, 'error');
    }
    
    addHistoryItem('bj', `
        <div><strong>P:${playerTotal} D:${dealerTotal}</strong></div>
        <div style="color: ${isWin ? '#00b894' : '#ff7675'};">${winAmount > 0 ? '+' : ''}${(winAmount - blackjackState.currentBet).toFixed(2)}</div>
    `, isWin);
    
    // Reset UI
    document.getElementById('bj-deal').disabled = false;
    document.getElementById('bj-game-actions').style.display = 'none';
    document.getElementById('bj-bet-controls').style.display = 'block';
    
    blackjackState.isPlaying = false;
}

document.getElementById('bj-deal').addEventListener('click', () => {
    const betAmount = parseFloat(document.getElementById('bj-bet').value);
    
    if (betAmount < 1 || betAmount > balance) {
        showToast('Invalid bet amount!', 'error');
        return;
    }
    
    updateBalance(-betAmount);
    
    blackjackState.currentBet = betAmount;
    blackjackState.isPlaying = true;
    blackjackState.playerStood = false;
    blackjackState.deck = shuffleDeck(createDeck());
    blackjackState.playerHand = [];
    blackjackState.dealerHand = [];
    
    // Deal initial cards
    blackjackState.playerHand.push(blackjackState.deck.pop());
    blackjackState.dealerHand.push(blackjackState.deck.pop());
    blackjackState.playerHand.push(blackjackState.deck.pop());
    blackjackState.dealerHand.push(blackjackState.deck.pop());
    
    updateBlackjackDisplay();
    
    document.getElementById('bj-status').textContent = '';
    document.getElementById('bj-deal').disabled = true;
    document.getElementById('bj-bet-controls').style.display = 'none';
    document.getElementById('bj-game-actions').style.display = 'flex';
    
    // Check for natural blackjack
    if (calculateHandValue(blackjackState.playerHand) === 21) {
        setTimeout(() => dealerPlay(), 500);
    }
});

document.getElementById('bj-hit').addEventListener('click', () => {
    if (!blackjackState.isPlaying) return;
    
    const card = blackjackState.deck.pop();
    blackjackState.playerHand.push(card);
    updateBlackjackDisplay();
    
    const playerTotal = calculateHandValue(blackjackState.playerHand);
    
    if (playerTotal > 21) {
        setTimeout(() => dealerPlay(), 500);
    } else if (playerTotal === 21) {
        setTimeout(() => dealerPlay(), 500);
    }
});

document.getElementById('bj-stand').addEventListener('click', () => {
    if (!blackjackState.isPlaying) return;
    dealerPlay();
});

document.getElementById('bj-double').addEventListener('click', () => {
    if (!blackjackState.isPlaying) return;
    
    if (balance < blackjackState.currentBet) {
        showToast('Insufficient balance to double!', 'error');
        return;
    }
    
    updateBalance(-blackjackState.currentBet);
    blackjackState.currentBet *= 2;
    
    // Take one card and automatically stand
    const card = blackjackState.deck.pop();
    blackjackState.playerHand.push(card);
    updateBlackjackDisplay();
    
    setTimeout(() => {
        const playerTotal = calculateHandValue(blackjackState.playerHand);
        if (playerTotal <= 21) {
            dealerPlay();
        } else {
            dealerPlay();
        }
    }, 500);
});

// ==========================================
// INITIALIZATION
// ==========================================

console.log('🎰 CryptoLux Casino loaded successfully!');
console.log('💎 All games use cryptographic RNG for provably fair results');
console.log('🎮 Have fun and gamble responsibly!');
