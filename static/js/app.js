// Update recommendations periodically
function updateRecommendations(force = false) {
    if (!force && window.isUpdating) return;
    
    window.isUpdating = true;
    $('#loading').show();
    
    $.get('/recommend', function(data) {
        if (data.success) {
            updateEmotionDisplay(data.emotion);
            updateTrackDisplay(data.tracks, data.spotify_playlist_url);
        } else {
            handleRecommendationError(data.message);
        }
        $('#loading').hide();
        window.isUpdating = false;
    }).fail(function(jqXHR, textStatus, errorThrown) {
        handleRecommendationError(jqXHR.responseJSON?.message || 'Failed to get recommendations');
    });
}

// Update emotion status
function updateEmotionStatus() {
    $.get('/get_emotion', function(data) {
        const newEmotion = data.emotion.toLowerCase();
        if (window.lastEmotion !== newEmotion) {
            window.lastEmotion = newEmotion;
            updateRecommendations(true);
        }
    });
}

// Helper function to update emotion display
function updateEmotionDisplay(emotion) {
    const icon = getEmotionIcon(emotion);
    $('#emotion-display').html(`${icon} Current Emotion: ${emotion}`);
}

// Helper function to get emotion icon
function getEmotionIcon(emotion) {
    const iconMap = {
        'happy': '<i class="fas fa-face-smile"></i>',
        'sad': '<i class="fas fa-face-sad-tear"></i>',
        'angry': '<i class="fas fa-face-angry"></i>',
        'neutral': '<i class="fas fa-face-meh"></i>',
        'surprise': '<i class="fas fa-face-surprise"></i>',
        'fear': '<i class="fas fa-face-fearful"></i>',
        'disgust': '<i class="fas fa-face-frown"></i>'
    };
    return iconMap[emotion.toLowerCase()] || '<i class="fas fa-face-meh"></i>';
}

// Helper function to update track display
function updateTrackDisplay(tracks, playlistUrl) {
    const sections = {
        upper: tracks.slice(0, 4),    // First 4 tracks
        middle: tracks.slice(4, 8),   // Next 4 tracks
        lower: tracks.slice(8, 12)    // Last 4 tracks
    };
    
    Object.entries(sections).forEach(([section, sectionTracks]) => {
        // Ensure exactly 4 tracks by padding with empty tracks if needed
        while (sectionTracks.length < 4) {
            sectionTracks.push({
                id: `empty-${section}-${sectionTracks.length}`,
                name: 'No track available',
                artist: '',
                album_cover: '/static/img/empty-album.png',
                spotify_url: '#',
                empty: true
            });
        }
        
        const html = sectionTracks.map(track => createTrackCard(track)).join('');
        $(`#${section}-tracks`).html(html);
    });
    
    if (playlistUrl) {
        $('#spotify-playlist-button').attr('href', playlistUrl).show();
    } else {
        $('#spotify-playlist-button').hide();
    }

    // Initialize track controls after updating display
    initializeTrackControls();
}

// Helper function to handle recommendation errors
function handleRecommendationError(message) {
    $('#emotion-display').html(`<i class="fas fa-face-frown"></i> ${message || 'No recommendations available'}`);
    $('#upper-tracks, #middle-tracks, #lower-tracks').html('');
    $('#spotify-playlist-button').hide();
    $('#loading').hide();
    window.isUpdating = false;
}

// Theme switching functionality
function initTheme() {
    const toggleSwitch = document.querySelector('#checkbox');
    const currentTheme = localStorage.getItem('theme');

    if (currentTheme) {
        document.body.classList[currentTheme === 'light' ? 'add' : 'remove']('light-mode');
        toggleSwitch.checked = currentTheme === 'light';
    }

    toggleSwitch.addEventListener('change', function(e) {
        if (e.target.checked) {
            document.body.classList.add('light-mode');
            localStorage.setItem('theme', 'light');
        } else {
            document.body.classList.remove('light-mode');
            localStorage.setItem('theme', 'dark');
        }
    });
}

// Create HTML for track cards
function createTrackCard(track) {
    // Truncate long text while preserving full text in data attribute
    const truncateText = (text, maxLength = 25) => {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    };

    const truncatedName = truncateText(track.name);
    const truncatedArtist = truncateText(track.artist || '');
    const isFavorite = isTrackFavorite(track.id);

    // If it's an empty track, return a placeholder card
    if (track.empty) {
        return `
            <div class="track-card empty">
                <div class="empty-card-content">
                    <i class="fas fa-music"></i>
                    <p>No track available</p>
                </div>
            </div>
        `;
    }

    return `
        <div class="track-card" data-track-id="${track.id}">
            <button class="favorite-btn ${isFavorite ? 'active' : ''}" data-track-id="${track.id}">
                <i class="fas fa-heart"></i>
            </button>
            <img src="${track.album_cover}" alt="${track.name}" class="album-cover">
            <div class="track-info">
                <h5 class="track-title" data-full-text="${track.name}" title="${track.name}">
                    ${truncatedName}
                </h5>
                <p class="track-artist" data-full-text="${track.artist}" title="${track.artist}">
                    ${truncatedArtist}
                </p>
            </div>
            <div class="track-controls">
                <a href="${track.spotify_url}" target="_blank" class="btn btn-spotify btn-sm">
                    <i class="fas fa-play"></i> Play
                </a>
                <button class="btn btn-outline-light btn-sm skip-btn" data-track-id="${track.id}">
                    <i class="fas fa-forward"></i> Skip
                </button>
                <button class="btn btn-outline-light btn-sm feedback-btn" data-track-id="${track.id}">
                    <i class="fas fa-star"></i> Rate
                </button>
            </div>
        </div>
    `;
}

// Play track function
function playTrack(trackId) {
    $.ajax({
        url: '/play',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ track_id: trackId }),
        success: function(response) {
            if (!response.success) {
                alert(response.message || 'Please make sure Spotify is open and active on your device.');
            }
        },
        error: function(jqXHR) {
            const message = jqXHR.responseJSON?.message || 'Failed to play track. Please try again.';
            alert(message);
        }
    });
}

// Initialize track controls
function initializeTrackControls() {
    // Handle favorite button clicks
    $('.favorite-btn').off('click').on('click', function(e) {
        e.preventDefault();
        const trackId = $(this).data('track-id');
        toggleFavorite(trackId);
        $(this).toggleClass('active');
    });

    // Handle skip button clicks
    $('.skip-btn').off('click').on('click', function(e) {
        e.preventDefault();
        const trackId = $(this).data('track-id');
        skipTrack(trackId);
    });

    // Handle feedback button clicks
    $('.feedback-btn').off('click').on('click', function(e) {
        e.preventDefault();
        const trackId = $(this).data('track-id');
        openTrackFeedbackModal(trackId);
    });
}

// Initialize favorites from localStorage and session
let userFavorites = new Set();

// Function to load favorites from server
function loadFavorites() {
    $.get('/get_user_data', function(response) {
        if (response.success) {
            userFavorites = new Set(response.favorites);
            // Update UI for any visible tracks
            $('.track-card').each(function() {
                const trackId = $(this).data('track-id');
                if (trackId) {
                    const favBtn = $(this).find('.favorite-btn');
                    favBtn.toggleClass('active', userFavorites.has(trackId));
                }
            });
        }
    });
}

// Function to check if a track is favorite
function isTrackFavorite(trackId) {
    return userFavorites.has(trackId);
}

// Function to toggle favorite status
function toggleFavorite(trackId) {
    const $btn = $(`.favorite-btn[data-track-id="${trackId}"]`);
    $btn.prop('disabled', true); // Prevent double-clicks

    $.ajax({
        url: '/favorite',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ track_id: trackId }),
        success: function(response) {
            if (response.success) {
                if (response.is_favorite) {
                    userFavorites.add(trackId);
                    showToast('Added to favorites!', 'success');
                } else {
                    userFavorites.delete(trackId);
                    showToast('Removed from favorites', 'info');
                }

                // Update UI
                $btn.toggleClass('active', response.is_favorite);
                
                // If favorites section is open, refresh it
                if ($('.user-data-section').length && $('.user-data-section h3').text() === 'My Favorite Tracks') {
                    showUserData('favorites');
                }
            } else {
                showToast(response.message || 'Failed to update favorites', 'error');
            }
        },
        error: function() {
            showToast('Failed to update favorites', 'error');
        },
        complete: function() {
            $btn.prop('disabled', false);
        }
    });
}

// Function to initialize feedback system
function initializeFeedbackSystem() {
    // Add emotion feedback modal to the DOM if it doesn't exist
    if (!$('#emotionFeedbackModal').length) {
        $('body').append(`
            <div class="modal fade" id="emotionFeedbackModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Rate Emotion Detection</h5>
                            <button type="button" class="modal-close" data-bs-dismiss="modal" aria-label="Close">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        <div class="modal-body">
                            <div class="emotion-rating">
                                <label class="rating-label">How accurate was the emotion detection?</label>
                                <div class="rating" data-max="5">
                                    <i class="far fa-star" data-rating="1" data-tooltip="Poor"></i>
                                    <i class="far fa-star" data-rating="2" data-tooltip="Fair"></i>
                                    <i class="far fa-star" data-rating="3" data-tooltip="Good"></i>
                                    <i class="far fa-star" data-rating="4" data-tooltip="Very Good"></i>
                                    <i class="far fa-star" data-rating="5" data-tooltip="Excellent"></i>
                                </div>
                                <div class="rating-description">Click on a star to rate</div>
                            </div>
                            <textarea id="emotionFeedbackComment" 
                                    class="feedback-textarea" 
                                    placeholder="Additional comments (optional)"
                                    rows="3"></textarea>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-submit-feedback" id="submitEmotionFeedback">
                                Submit Feedback
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `);
    }

    // Handle star rating clicks
    $('.rating i').on('click', function() {
        const rating = $(this).data('rating');
        const $container = $(this).closest('.rating');
        const $description = $container.siblings('.rating-description');
        
        // Update stars
        $container.find('i').removeClass('fas').addClass('far');
        $container.find('i').each(function() {
            if ($(this).data('rating') <= rating) {
                $(this).removeClass('far').addClass('fas');
            }
        });
        
        // Update rating value
        $container.data('current-rating', rating);
        
        // Update description
        const descriptions = [
            'Poor', 'Fair', 'Good', 'Very Good', 'Excellent'
        ];
        $description.text(descriptions[rating - 1]);
    });

    // Handle star rating hover effects
    $('.rating i').on('mouseenter', function() {
        const rating = $(this).data('rating');
        const $container = $(this).closest('.rating');
        
        $container.find('i').each(function() {
            if ($(this).data('rating') <= rating) {
                $(this).addClass('hover');
            }
        });
    }).on('mouseleave', function() {
        $(this).closest('.rating').find('i').removeClass('hover');
    });

    // Reset modal when hidden
    $('.modal').on('hidden.bs.modal', function() {
        const $modal = $(this);
        $modal.find('.rating i').removeClass('fas').addClass('far').removeClass('hover');
        $modal.find('textarea').val('');
        $modal.find('.rating').removeData('current-rating');
        $modal.find('.rating-description').text('Click on a star to rate');
    });

    // Handle emotion feedback submission
    $('#submitEmotionFeedback').on('click', function() {
        const $modal = $('#emotionFeedbackModal');
        const rating = $modal.find('.rating').data('current-rating');
        const comment = $('#emotionFeedbackComment').val();
        
        if (!rating) {
            alert('Please provide a rating');
            return;
        }

        submitFeedback('emotion', rating, comment)
            .then(() => {
                $modal.modal('hide');
                showToast('Thank you for your feedback!', 'success');
            })
            .catch(error => {
                showToast(error.message || 'Failed to submit feedback', 'error');
            });
    });

    // Handle track feedback submission
    $('#submitTrackFeedback').on('click', function() {
        const $modal = $('#trackFeedbackModal');
        const rating = $modal.find('.rating').data('current-rating');
        const comment = $('#trackFeedbackComment').val();
        const trackId = $modal.data('track-id');
        
        if (!rating) {
            alert('Please provide a rating');
            return;
        }

        submitFeedback('track', rating, comment, trackId)
            .then(() => {
                $modal.modal('hide');
                showToast('Thank you for rating this track!', 'success');
            })
            .catch(error => {
                showToast(error.message || 'Failed to submit feedback', 'error');
            });
    });
}

function submitFeedback(type, rating, comment, trackId = null) {
    return new Promise((resolve, reject) => {
        $.ajax({
            url: '/feedback',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                type: type,
                rating: rating,
                comment: comment,
                track_id: trackId
            }),
            success: function(response) {
                if (response.success) {
                    resolve(response);
                } else {
                    reject(new Error(response.message || 'Failed to submit feedback'));
                }
            },
            error: function(jqXHR) {
                reject(new Error(jqXHR.responseJSON?.message || 'Failed to submit feedback'));
            }
        });
    });
}

function openTrackFeedbackModal(trackId) {
    $('#trackFeedbackModal')
        .data('track-id', trackId)
        .modal('show');
}

// Skip track functionality
function skipTrack(trackId) {
    const $trackCard = $(`.track-card[data-track-id="${trackId}"]`);
    $trackCard.addClass('skipping');
    
    $.ajax({
        url: '/skip',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ track_id: trackId }),
        success: function(response) {
            if (response.success) {
                $trackCard.fadeOut(300, function() {
                    updateRecommendations(true);
                });
            } else {
                $trackCard.removeClass('skipping');
                showToast(response.message || 'Failed to skip track', 'error');
            }
        },
        error: function(jqXHR) {
            $trackCard.removeClass('skipping');
            showToast(jqXHR.responseJSON?.message || 'Failed to skip track', 'error');
        }
    });
}

// Toast notification system
function showToast(message, type = 'info') {
    // Remove existing toasts
    $('.toast').remove();

    const toast = $(`
        <div class="toast ${type}" role="alert">
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `).appendTo('body');

    toast.fadeIn().delay(3000).fadeOut(function() {
        $(this).remove();
    });
}

// Add toast styles to the existing CSS
$('<style>')
    .text(`
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            min-width: 200px;
            padding: 15px;
            background: var(--card-bg-dark);
            color: var(--text-color-dark);
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            z-index: 1000;
            display: none;
        }
        .toast.success {
            border-left: 4px solid #1DB954;
        }
        .toast.error {
            border-left: 4px solid #ff4444;
        }
        .toast.info {
            border-left: 4px solid #0088cc;
        }
        .skipping {
            opacity: 0.5;
            pointer-events: none;
        }
    `)
    .appendTo('head');

// Function to toggle side panel
function toggleSidePanel() {
    $('.side-panel').toggleClass('expanded');
    $('.main-content').toggleClass('shifted');
}

// Function to close side panel
function closeSidePanel() {
    $('.side-panel').removeClass('expanded');
    $('.main-content').removeClass('shifted');
}

// Show user data (favorites and history)
function showUserData(type) {
    // Close any existing panel first
    closeSidePanel();
    
    // Show loading state in side panel
    $('.side-panel').html(`
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h3>${type === 'favorites' ? 'My Favorites' : 'History'}</h3>
            <button class="btn btn-link close-panel">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="d-flex justify-content-center align-items-center" style="height: 200px;">
            <div class="spinner-border text-light" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `);

    // Show the panel
    toggleSidePanel();

    // Load the data
    $.get('/get_user_data', function(response) {
        if (response.success) {
            const data = type === 'favorites' ? response.favorites : response.skipped_tracks;
            
            if (!data || data.length === 0) {
                // Show empty state
                $('.side-panel').html(`
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <h3>${type === 'favorites' ? 'My Favorites' : 'History'}</h3>
                        <button class="btn btn-link close-panel">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="side-panel-empty">
                        <i class="fas fa-${type === 'favorites' ? 'heart' : 'history'}"></i>
                        <p>${type === 'favorites' ? 'No favorite tracks yet' : 'No listening history yet'}</p>
                    </div>
                `);
                return;
            }

            // Fetch full track details
            $.ajax({
                url: '/get_tracks_info',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ track_ids: data }),
                success: function(trackResponse) {
                    if (trackResponse.success && trackResponse.tracks) {
                        const tracks = trackResponse.tracks;
                        const html = `
                            <div class="d-flex justify-content-between align-items-center mb-4">
                                <h3>${type === 'favorites' ? 'My Favorites' : 'History'}</h3>
                                <button class="btn btn-link close-panel">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                            ${tracks.map(track => createSideTrackCard(track)).join('')}
                        `;
                        $('.side-panel').html(html);
                        initializeTrackControls();
                    } else {
                        showToast('Failed to load track information', 'error');
                    }
                },
                error: function() {
                    showToast('Failed to load track information', 'error');
                }
            });
        } else {
            showToast('Failed to load user data', 'error');
        }
    });
}

// Function to create a side track card
function createSideTrackCard(track) {
    const isFavorite = isTrackFavorite(track.id);
    return `
        <div class="side-track-card" data-track-id="${track.id}">
            <img src="${track.album_cover}" alt="${track.name}" loading="lazy">
            <div class="side-track-info">
                <h5 title="${track.name}">${track.name}</h5>
                <p title="${track.artist}">${track.artist}</p>
            </div>
            <div class="side-track-controls">
                <button class="play-btn" title="Play on Spotify" onclick="playTrack('${track.id}')">
                    <i class="fas fa-play"></i>
                </button>
                <button class="favorite-btn ${isFavorite ? 'active' : ''}" 
                        data-track-id="${track.id}" 
                        title="${isFavorite ? 'Remove from favorites' : 'Add to favorites'}">
                    <i class="fas fa-heart"></i>
                </button>
            </div>
        </div>
    `;
}

// Function to show side panel with loading state
function showSidePanel(type) {
    // Close any existing panel first
    closeSidePanel();
    
    // Show loading state in side panel
    $('.side-panel').html(`
        <div class="side-panel-header">
            <h3>${type === 'favorites' ? 'My Favorites' : 'History'}</h3>
            <button class="close-panel" aria-label="Close panel">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="side-panel-loading">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <div>Loading ${type === 'favorites' ? 'favorites' : 'history'}...</div>
        </div>
    `);

    // Show the panel with animation
    requestAnimationFrame(() => {
        $('.side-panel').addClass('expanded');
    });

    return loadSidePanelContent(type);
}

// Function to load side panel content
function loadSidePanelContent(type) {
    return $.get('/get_user_data')
        .then(response => {
            if (!response.success) {
                throw new Error('Failed to load user data');
            }

            const data = type === 'favorites' ? response.favorites : response.skipped_tracks;
            
            if (!data || data.length === 0) {
                return showEmptySidePanel(type);
            }

            return $.ajax({
                url: '/get_tracks_info',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ track_ids: data })
            }).then(trackResponse => {
                if (!trackResponse.success || !trackResponse.tracks) {
                    throw new Error('Failed to load track information');
                }

                showTracksSidePanel(type, trackResponse.tracks);
            });
        })
        .catch(error => {
            showToast(error.message, 'error');
            closeSidePanel();
        });
}

// Function to show empty state in side panel
function showEmptySidePanel(type) {
    $('.side-panel').html(`
        <div class="side-panel-header">
            <h3>${type === 'favorites' ? 'My Favorites' : 'History'}</h3>
            <button class="close-panel" aria-label="Close panel">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="side-panel-empty">
            <i class="fas fa-${type === 'favorites' ? 'heart' : 'history'}"></i>
            <p>${type === 'favorites' ? 'No favorite tracks yet' : 'No listening history yet'}</p>
        </div>
    `);
}

// Function to show tracks in side panel
function showTracksSidePanel(type, tracks) {
    const html = `
        <div class="side-panel-header">
            <h3>${type === 'favorites' ? 'My Favorites' : 'History'}</h3>
            <button class="close-panel" aria-label="Close panel" data-tooltip="Close panel">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="side-panel-search">
            <div class="search-input-group">
                <i class="fas fa-search"></i>
                <input type="text" 
                       placeholder="Search by title or artist..." 
                       class="track-search"
                       data-tooltip="Type to filter tracks">
            </div>
        </div>
        <div class="side-panel-content">
            ${tracks.map(track => createSideTrackCard(track)).join('')}
        </div>
    `;
    
    $('.side-panel').html(html);
    
    // Initialize track controls
    initializeTrackControls();
    
    // Add search functionality
    $('.track-search').on('input', function() {
        filterTracks($(this).val());
    });
    
    // Update recently played section
    updateRecentlyPlayedSection();
}

// Function to close side panel with animation
function closeSidePanel() {
    const $panel = $('.side-panel');
    if ($panel.hasClass('expanded')) {
        $panel.removeClass('expanded');
        // Wait for animation to complete before clearing content
        setTimeout(() => {
            if (!$panel.hasClass('expanded')) {
                $panel.empty();
            }
        }, 300); // Match the CSS transition duration
    }
}

// Keyboard shortcuts handler
function handleKeyboardShortcuts(e) {
    // Only handle shortcuts if no input/textarea is focused
    if (e.target.tagName.toLowerCase() === 'input' || 
        e.target.tagName.toLowerCase() === 'textarea') {
        return;
    }

    switch(e.key.toLowerCase()) {
        case 'f':
            // Show favorites
            showSidePanel('favorites');
            break;
        case 'h':
            // Show history
            showSidePanel('history');
            break;
        case 'escape':
            // Close side panel
            closeSidePanel();
            break;
        case ' ':
            // Space bar to play/pause current track
            if (currentTrack) {
                e.preventDefault(); // Prevent page scroll
                togglePlayback();
            }
            break;
        case 'arrowright':
            // Skip to next track
            if (e.altKey) {
                e.preventDefault();
                skipTrack();
            }
            break;
        case 'l':
            // Toggle light/dark mode
            e.preventDefault(); // Prevent any default 'l' behavior
            $('#checkbox').click(); // Updated from #themeSwitch to #checkbox
            showToast('Theme toggled', 'info');
            break;
    }
}

// Track recently played songs (max 5)
let recentlyPlayed = [];
const MAX_RECENT = 5;

// Function to add a track to recently played
function addToRecentlyPlayed(track) {
    // Remove the track if it's already in the list
    recentlyPlayed = recentlyPlayed.filter(t => t.id !== track.id);
    
    // Add the track to the beginning
    recentlyPlayed.unshift({
        ...track,
        playedAt: new Date()
    });
    
    // Keep only the last MAX_RECENT tracks
    if (recentlyPlayed.length > MAX_RECENT) {
        recentlyPlayed.pop();
    }
    
    // Update recently played section if visible
    updateRecentlyPlayedSection();
}

// Function to format relative time
function getRelativeTime(date) {
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);
    
    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return `${Math.floor(diffInSeconds / 86400)}d ago`;
}

// Function to update recently played section
function updateRecentlyPlayedSection() {
    const recentlyPlayedHtml = `
        <div class="recently-played">
            <h4><i class="fas fa-clock"></i> Recently Played</h4>
            <div class="recently-played-list">
                ${recentlyPlayed.map(track => `
                    <div class="recently-played-item" data-track-id="${track.id}" 
                         data-tooltip="Click to play">
                        <img src="${track.album_cover}" alt="${track.name}">
                        <div class="recently-played-info">
                            <h5>${track.name}</h5>
                            <p>${track.artist}</p>
                        </div>
                        <span class="recently-played-time">
                            ${getRelativeTime(track.playedAt)}
                        </span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
    
    $('.recently-played').remove();
    if (recentlyPlayed.length > 0) {
        $('.side-panel-content').prepend(recentlyPlayedHtml);
        
        // Add click handler for recently played items
        $('.recently-played-item').on('click', function() {
            const trackId = $(this).data('track-id');
            playTrack(trackId);
        });
    }
}

// Enhanced playTrack function to include recently played
const originalPlayTrack = playTrack;
playTrack = function(trackId) {
    // Find the track in the DOM
    const $trackCard = $(`.track-card[data-track-id="${trackId}"]`);
    const track = {
        id: trackId,
        name: $trackCard.find('.track-title').text(),
        artist: $trackCard.find('.track-artist').text(),
        album_cover: $trackCard.find('.album-cover').attr('src')
    };
    
    // Add to recently played
    addToRecentlyPlayed(track);
    
    // Call original playTrack function
    return originalPlayTrack(trackId);
};

// Function to filter tracks in side panel
function filterTracks(searchTerm) {
    const $tracks = $('.side-track-card');
    if (!searchTerm) {
        $tracks.show();
        return;
    }
    
    searchTerm = searchTerm.toLowerCase();
    $tracks.each(function() {
        const $track = $(this);
        const title = $track.find('h5').text().toLowerCase();
        const artist = $track.find('p').text().toLowerCase();
        
        if (title.includes(searchTerm) || artist.includes(searchTerm)) {
            $track.show();
        } else {
            $track.hide();
        }
    });
}

// Add tooltips to existing elements
function initializeTooltips() {
    // Add tooltips to various controls
    $('.favorite-btn').attr('data-tooltip', function() {
        return $(this).hasClass('active') ? 'Remove from favorites' : 'Add to favorites';
    });
    
    $('.play-btn').attr('data-tooltip', 'Play on Spotify');
    $('.skip-btn').attr('data-tooltip', 'Skip this track');
    $('.feedback-btn').attr('data-tooltip', 'Rate this track');
    
    // Theme switch tooltip
    $('.theme-switch-wrapper').attr('data-tooltip', 'Toggle light/dark mode (Press L)');
}

// Initialize when document is ready
$(document).ready(function() {
    // Initialize theme
    initTheme();
    
    // Initialize variables
    window.lastEmotion = null;
    window.isUpdating = false;
    
    // Load favorites from server
    loadFavorites();
    
    // Initialize feedback system
    initializeFeedbackSystem();
    
    // Initial updates
    updateRecommendations(true);
    
    // Check emotion status every 500ms
    setInterval(updateEmotionStatus, 500);
    
    // Update recommendations every 30 seconds regardless of emotion
    setInterval(() => updateRecommendations(false), 30000);

    // Handle favorites and history buttons
    $('#showFavorites').on('click', () => showSidePanel('favorites'));
    $('#showHistory').on('click', () => showSidePanel('history'));

    // Handle close panel button clicks
    $(document).on('click', '.close-panel', function(e) {
        e.preventDefault();
        e.stopPropagation();
        closeSidePanel();
    });

    // Close panel when clicking outside
    $(document).on('click', function(e) {
        if ($('.side-panel').hasClass('expanded') &&
            !$(e.target).closest('.side-panel').length &&
            !$(e.target).closest('#showFavorites').length &&
            !$(e.target).closest('#showHistory').length) {
            closeSidePanel();
        }
    });

    // Handle escape key to close panel
    $(document).on('keydown', function(e) {
        if (e.key === 'Escape' && $('.side-panel').hasClass('expanded')) {
            closeSidePanel();
        }
    });

    // Add keyboard shortcuts
    $(document).on('keydown', handleKeyboardShortcuts);

    // Add tooltips to show keyboard shortcuts
    $('#showFavorites').attr('title', 'Show Favorites (Press F)');
    $('#showHistory').attr('title', 'Show History (Press H)');
    $('.theme-switch-wrapper').attr('data-tooltip', 'Toggle light/dark mode (Press L)');

    // Add visual indicator for keyboard shortcuts
    $('.nav-buttons button').append('<span class="shortcut-hint"></span>');
    $('#showFavorites .shortcut-hint').text('F');
    $('#showHistory .shortcut-hint').text('H');
    
    // Add theme shortcut hint
    $('.theme-switch-wrapper').append('<span class="shortcut-hint">L</span>');

    // Initialize tooltips
    initializeTooltips();
    
    // Update tooltips when favorite status changes
    $(document).on('click', '.favorite-btn', function() {
        const $btn = $(this);
        setTimeout(() => {
            $btn.attr('data-tooltip', 
                $btn.hasClass('active') ? 'Remove from favorites' : 'Add to favorites'
            );
        }, 100);
    });
}); 