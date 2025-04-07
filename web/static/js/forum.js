document.addEventListener("DOMContentLoaded", function () {
  // Get CSRF token
  console.log("Initializing voting system...");

  function getCsrfToken() {
    return document.querySelector("[name=csrfmiddlewaretoken]").value;
  }

  // Function to handle language prefix (this is referenced but not defined in the provided code)
  function getLanguagePrefix() {
    // Default to empty string if there's no language prefix
    return document.body.dataset.languagePrefix || "";
  }

  // Handle vote buttons for topics
  document.querySelectorAll(".vote-btn[data-topic]").forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();

      console.log("Topic vote button clicked");

      // Check authentication
      if (!document.body.classList.contains("user-authenticated")) {
        window.location.href = "/accounts/login/";
        return;
      }

      const topicId = this.dataset.topic;
      const voteType = this.dataset.voteType;
      const csrftoken = getCsrfToken();
      const languagePrefix = getLanguagePrefix();

      console.log(
        `Sending POST request for topic ${topicId}, vote type: ${voteType}`
      );

      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${languagePrefix}/forum/topic/${topicId}/vote/`);
      xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
      xhr.setRequestHeader("X-CSRFToken", csrftoken);

      xhr.onload = function () {
        if (xhr.status === 200) {
          const data = JSON.parse(xhr.responseText);
          console.log("Vote response:", data);

          if (data.success) {
            const voteControls = document.querySelectorAll(
              `.vote-btn[data-topic="${topicId}"]`
            );

            voteControls.forEach((btn) => {
              const scoreElement = btn
                .closest(".flex-col")
                .querySelector(".vote-score");
              if (scoreElement) {
                scoreElement.textContent = data.score;
              }

              const svg = btn.querySelector("svg");
              if (btn.dataset.voteType === "up") {
                if (data.action !== "removed" && voteType === "up") {
                  svg.classList.add("text-teal-500");
                } else {
                  svg.classList.remove("text-teal-500");
                }
              } else if (btn.dataset.voteType === "down") {
                if (data.action !== "removed" && voteType === "down") {
                  svg.classList.add("text-red-500");
                } else {
                  svg.classList.remove("text-red-500");
                }
              }
            });
          }
        } else {
          console.error("Error voting on topic, status:", xhr.status);
        }
      };

      xhr.onerror = function () {
        console.error("Network error occurred");
      };

      xhr.send(`vote_type=${voteType}`);
    });
  });

  // Handle vote buttons for replies
  document.querySelectorAll(".vote-btn[data-reply]").forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();

      console.log("Reply vote button clicked");

      // Check authentication
      if (!document.body.classList.contains("user-authenticated")) {
        window.location.href = "/accounts/login/";
        return;
      }

      const replyId = this.dataset.reply;
      const voteType = this.dataset.voteType;
      const csrftoken = getCsrfToken();
      const languagePrefix = getLanguagePrefix();

      console.log(
        `Sending POST request for reply ${replyId}, vote type: ${voteType}`
      );

      // For consistency with topic voting, using XMLHttpRequest instead of fetch
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${languagePrefix}/forum/reply/${replyId}/vote/`);
      xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
      xhr.setRequestHeader("X-CSRFToken", csrftoken);

      xhr.onload = function () {
        if (xhr.status === 200) {
          const data = JSON.parse(xhr.responseText);
          console.log("Vote response:", data);

          if (data.success) {
            // Find this specific reply's vote controls
            const voteControlsCol = button.closest(".flex-col");
            const scoreElement = voteControlsCol.querySelector(".vote-score");

            // Update score
            scoreElement.textContent = data.score;

            // Update active state
            const upvoteBtn = voteControlsCol.querySelector(
              '[data-vote-type="up"] svg'
            );
            const downvoteBtn = voteControlsCol.querySelector(
              '[data-vote-type="down"] svg'
            );

            // Reset both buttons
            upvoteBtn.classList.remove("text-teal-500");
            downvoteBtn.classList.remove("text-red-500");

            // Set active state based on action
            if (data.action !== "removed") {
              if (voteType === "up") {
                upvoteBtn.classList.add("text-teal-500");
              } else {
                downvoteBtn.classList.add("text-red-500");
              }
            }
          }
        } else {
          console.error("Error voting on reply, status:", xhr.status);
        }
      };

      xhr.onerror = function () {
        console.error("Network error occurred");
      };

      xhr.send(`vote_type=${voteType}`);
    });
  });
});
