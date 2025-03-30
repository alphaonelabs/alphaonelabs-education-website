from captcha.fields import CaptchaTextInput
from django import forms


class TailwindInput(forms.TextInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "class": (
                    "block w-full border rounded p-2 focus:outline-none focus:ring-2 "
                    "focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800 "
                    "border-gray-300 dark:border-gray-600"
                )
            }
        )


class TailwindTextarea(forms.Textarea):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "class": (
                    "block w-full border rounded p-2 focus:outline-none focus:ring-2 "
                    "focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800 "
                    "border-gray-300 dark:border-gray-600"
                ),
                "rows": kwargs.pop("rows", 4),
            }
        )


class TailwindEmailInput(forms.EmailInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "class": (
                    "block w-full border rounded p-2 focus:outline-none focus:ring-2 "
                    "focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800 "
                    "border-gray-300 dark:border-gray-600"
                )
            }
        )


class TailwindNumberInput(forms.NumberInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "class": (
                    "block w-full border rounded p-2 focus:outline-none focus:ring-2 "
                    "focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800 "
                    "border-gray-300 dark:border-gray-600"
                )
            }
        )


class TailwindSelect(forms.Select):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "class": (
                    "block w-full border rounded p-2 focus:outline-none focus:ring-2 "
                    "focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800 "
                    "border-gray-300 dark:border-gray-600"
                )
            }
        )


class TailwindCheckboxInput(forms.CheckboxInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "class": (
                    "h-4 w-4 rounded border-gray-300 text-teal-600 focus:ring-teal-500 "
                    "dark:border-gray-600 dark:bg-gray-800 dark:ring-offset-gray-800"
                )
            }
        )


class TailwindFileInput(forms.FileInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "class": (
                    "block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 "
                    "file:rounded file:border-0 file:text-sm file:font-semibold file:bg-teal-50 "
                    "file:text-teal-700 hover:file:bg-teal-100 dark:file:bg-teal-900 "
                    "dark:file:text-teal-200 dark:text-gray-400"
                )
            }
        )


class TailwindDateTimeInput(forms.DateTimeInput):
    def __init__(self, *args, **kwargs):
        kwargs["format"] = "%Y-%m-%dT%H:%M"  # HTML5 datetime-local format
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "class": (
                    "block w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 "
                    "focus:ring-blue-500 dark:bg-gray-700 "
                    "border-gray-300 dark:border-gray-600 dark:text-white cursor-pointer"
                ),
                "type": "datetime-local",
                "placeholder": "Select date and time",
                "required": True,
                "autocomplete": "off",
            }
        )


class TailwindCaptchaTextInput(CaptchaTextInput):
    template_name = "captcha/widget.html"

    def __init__(self, attrs=None):
        default_attrs = {
            "class": (
                "block w-full border rounded p-2 focus:outline-none focus:ring-2 "
                "focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800 "
                "border-gray-300 dark:border-gray-600"
            ),
            "placeholder": "Enter CAPTCHA",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)


class TailwindJSONWidget(forms.Widget):
    template_name = "admin/widgets/json_features_widget.html"

    def __init__(self, attrs=None):
        default_attrs = {
            "class": "json-features-widget",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        import json

        if value is None:
            decoded_value = []
        elif isinstance(value, str):
            try:
                decoded_value = json.loads(value)
            except (ValueError, TypeError):
                decoded_value = []
        else:
            decoded_value = value

        # Ensure value is a list
        if not isinstance(decoded_value, list):
            decoded_value = []

        # Create HTML with format for readability
        feature_items = []
        for i, feature in enumerate(decoded_value):
            item_html = f"""
            <div class="flex items-center group" data-index="{i}">
                <div class="flex-grow p-2 border rounded-lg bg-white dark:bg-gray-800
                     group-hover:border-teal-400 transition-all duration-200">
                    <input type="text" value="{feature}"
                           class="w-full border-none p-1 focus:outline-none focus:ring-1
                                  focus:ring-teal-300 bg-transparent" />
                </div>
                <button type="button" class="ml-2 text-gray-400 hover:text-red-500
                        transition-colors duration-200 delete-item">
                    <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd"
                              d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9z"  # noqa: E501
                              clip-rule="evenodd" />
                        <path fill-rule="evenodd"
                              d="M7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"  # noqa: E501
                              clip-rule="evenodd" />
                    </svg>
                </button>
                <button type="button" class="ml-1 text-gray-400 hover:text-blue-500
                        drag-handle cursor-grab">  # noqa: E501
                    <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd"
                              d="M10 3a1 1 0 01.707.293l3 3a1 1 0 01-1.414 1.414L10 5.414 7.707 7.707a1 1 0 01-1.414-1.414l3-3A1 1 0 0110 3z"
                              clip-rule="evenodd" />
                        <path fill-rule="evenodd"
                              d="M6.293 9.293a1 1 0 011.414 0L10 14.586l2.293-2.293a1 1 0 011.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z"
                              clip-rule="evenodd" />
                    </svg>
                </button>
            </div>
            """
            feature_items.append(item_html)

        return """
        <div class="membership-features-container" id="{0}-container">
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700">Features</label>
                <p class="text-sm text-gray-500 mb-2">Add features for this membership plan</p>
                <div class="space-y-2" id="{0}-items">
                    {1}
                </div>
                <input type="hidden" name="{0}" id="{0}-input" value='{2}'>
                <button type="button"
                        id="{0}-add-btn"
                        class="mt-3 inline-flex items-center px-3 py-1.5 border border-transparent
                               text-xs leading-4 font-medium rounded-md text-white bg-teal-600
                               hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-offset-2
                               focus:ring-teal-500 transition-all duration-200">
                    <svg class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd"
                              d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z"
                              clip-rule="evenodd" />
                    </svg>
                    Add Feature
                </button>
            </div>
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    const container = document.getElementById('{0}-container');
                    const inputField = document.getElementById('{0}-input');
                    const itemsContainer = document.getElementById('{0}-items');
                    const addButton = document.getElementById('{0}-add-btn');

                    // Initial data
                    let features = {2};

                    // Update the hidden input with the features array
                    function updateInput() {{
                        inputField.value = JSON.stringify(features);
                    }}

                    // Render all feature items
                    function renderItems() {{
                        itemsContainer.innerHTML = '';
                        features.forEach((feature, index) => {{
                            const itemHtml = `
                                <div class="flex items-center group animate-fadeIn" data-index="${{index}}">
                                    <div class="flex-grow p-2 border rounded-lg bg-white dark:bg-gray-800
                                         group-hover:border-teal-400 transition-all duration-200">
                                        <input type="text" value="${{feature}}"
                                               class="w-full border-none p-1 focus:outline-none focus:ring-1
                                                      focus:ring-teal-300 bg-transparent"
                                               oninput="this.parentNode.parentNode.dataset.value = this.value" />
                                    </div>
                                    <button type="button"
                                            class="ml-2 text-gray-400 hover:text-red-500
                                                   transition-colors duration-200 delete-item">
                                        <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                            <path fill-rule="evenodd"
                                                  d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9z"  # noqa: E501
                                                  clip-rule="evenodd" />
                                            <path fill-rule="evenodd"
                                                  d="M7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"  # noqa: E501
                                                  clip-rule="evenodd" />
                                        </svg>
                                    </button>
                                    <button type="button"
                                            class="ml-1 text-gray-400 hover:text-blue-500
                                                   drag-handle cursor-grab">  # noqa: E501
                                        <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                            <path fill-rule="evenodd"
                                                  d="M10 3a1 1 0 01.707.293l3 3a1 1 0 01-1.414 1.414L10 5.414 7.707 7.707a1 1 0 01-1.414-1.414l3-3A1 1 0 0110 3z"
                                                  clip-rule="evenodd" />
                                            <path fill-rule="evenodd"
                                                  d="M6.293 9.293a1 1 0 011.414 0L10 14.586l2.293-2.293a1 1 0 011.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z"
                                                  clip-rule="evenodd" />
                                        </svg>
                                    </button>
                                </div>
                            `;
                            const div = document.createElement('div');
                            div.innerHTML = itemHtml;
                            itemsContainer.appendChild(div.firstElementChild);
                        }});

                        // Add event listeners for delete buttons
                        document.querySelectorAll('#{0}-items .delete-item').forEach(button => {{
                            button.addEventListener('click', function() {{
                                const index = parseInt(this.closest('[data-index]').dataset.index);
                                features.splice(index, 1);
                                renderItems();
                                updateInput();
                            }});
                        }});

                        // Add event listeners for input changes
                        document.querySelectorAll('#{0}-items input').forEach(input => {{
                            input.addEventListener('input', function() {{
                                const index = parseInt(this.closest('[data-index]').dataset.index);
                                features[index] = this.value;
                                updateInput();
                            }});
                        }});

                        // Enable drag and drop reordering
                        makeItemsDraggable();
                    }}

                    function makeItemsDraggable() {{
                        const items = itemsContainer.querySelectorAll('[data-index]');
                        items.forEach(item => {{
                            const handle = item.querySelector('.drag-handle');
                            handle.addEventListener('mousedown', function(e) {{
                                e.preventDefault();

                                const draggedItem = item;
                                const initialIndex = parseInt(draggedItem.dataset.index);
                                let currentY = e.clientY;

                                const mouseMoveHandler = function(e) {{
                                    const deltaY = e.clientY - currentY;
                                    if (Math.abs(deltaY) > 10) {{
                                        draggedItem.classList.add('opacity-50');

                                        // Find the item to swap with
                                        const hoveredItem = document.elementFromPoint(e.clientX, e.clientY)
                                            .closest('#{{0}}-items [data-index]');

                                        if (hoveredItem && hoveredItem !== draggedItem) {{
                                            const hoverIndex = parseInt(hoveredItem.dataset.index);

                                            // Swap in the UI
                                            if (initialIndex < hoverIndex) {{
                                                itemsContainer.insertBefore(
                                                    draggedItem,
                                                    hoveredItem.nextSibling
                                                );
                                            }} else {{
                                                itemsContainer.insertBefore(draggedItem, hoveredItem);
                                            }}

                                            // Swap in the array
                                            const temp = features[initialIndex];
                                            features.splice(initialIndex, 1);
                                            features.splice(hoverIndex, 0, temp);

                                            // Update indices
                                            renderItems();
                                            updateInput();

                                            currentY = e.clientY;
                                        }}
                                    }}
                                }};

                                const mouseUpHandler = function() {{
                                    draggedItem.classList.remove('opacity-50');
                                    document.removeEventListener('mousemove', mouseMoveHandler);
                                    document.removeEventListener('mouseup', mouseUpHandler);
                                }};

                                document.addEventListener('mousemove', mouseMoveHandler);
                                document.addEventListener('mouseup', mouseUpHandler);
                            }});
                        }});
                    }}

                    // Add button event listener
                    addButton.addEventListener('click', function() {{
                        features.push('');
                        renderItems();
                        updateInput();

                        // Focus the newly added input
                        const newItem = itemsContainer.lastElementChild;
                        if (newItem) {{
                            newItem.querySelector('input').focus();
                        }}
                    }});

                    // Initial render
                    renderItems();
                }});
            </script>
        </div>
        """.format(
            name, "".join(feature_items), json.dumps(decoded_value)  # {0}  # {1}  # {2}
        )

    def value_from_datadict(self, data, files, name):
        import json

        json_value = data.get(name, "[]")
        try:
            value = json.loads(json_value)
            # Filter out empty strings
            if isinstance(value, list):
                value = [item for item in value if item.strip()]
            return value
        except (ValueError, TypeError):
            return []
