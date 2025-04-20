import html
import json

from captcha.fields import CaptchaTextInput
from django import forms
from django.forms.renderers import BaseRenderer


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
    """A custom widget for editing JSON arrays of strings as a list of inputs with drag-and-drop reordering."""

    def __init__(self, attrs: dict | None = None) -> None:
        default_attrs = {
            "class": "json-features-widget",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def render(
        self,
        name: str,
        value: list[str] | None,
        attrs: dict[str, str] | None = None,
        renderer: BaseRenderer | None = None,
    ) -> str:
        """
        Render the widget.

        Parameters:
            name: The name of the field
            value: List of feature strings or None
            attrs: Additional HTML attributes
            renderer: The form renderer (unused but required by Django's Widget interface)
        """
        if value is None:
            decoded_value = []
        elif isinstance(value, str):
            try:
                decoded_value = json.loads(value)
            except (ValueError, TypeError):
                decoded_value = []
        else:
            decoded_value = value

        # Generate feature items HTML
        feature_items = []
        for i, feature in enumerate(decoded_value):
            item_html = f"""
            <div class="flex items-center mb-2 bg-white dark:bg-gray-800 rounded-lg p-2 shadow-sm border
                 border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow duration-200" data-index="{i}">
                <div class="cursor-move mr-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300
                     transition-colors duration-200 drag-handle">
                    <i class="fas fa-grip-vertical"></i>
                </div>
                <div class="flex-grow">
                    <input type="text" value="{html.escape(str(feature))}"
                           class="w-full border-none p-1 focus:outline-none focus:ring-1
                                  focus:ring-teal-300 bg-transparent" />
                </div>
                <button type="button"
                        class="ml-2 text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300
                               transition-colors duration-200 delete-btn">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>
            """
            feature_items.append(item_html)

        # Render the complete widget
        return f"""
        <div class="mb-4">
            <input type="hidden" name="{name}" id="{name}" value='{json.dumps(decoded_value)}' />
            <div id="{name}-items" class="mb-3">
                {"".join(feature_items)}
            </div>
            <button type="button"
                    id="{name}-add"
                    class="bg-teal-500 hover:bg-teal-600 text-white py-1 px-3 rounded-md text-sm flex items-center">
                <i class="fas fa-plus mr-1"></i> Add Item
            </button>
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    const input = document.getElementById('{name}');
                    const itemsContainer = document.getElementById('{name}-items');
                    const addButton = document.getElementById('{name}-add');

                    // Parse the initial features
                    let features = {json.dumps(decoded_value)};

                    // Function to update the hidden input with the current features
                    function updateInput() {{
                        input.value = JSON.stringify(features);
                    }}

                    // Function to render the feature items
                    function renderItems() {{
                        itemsContainer.innerHTML = '';
                        features.forEach((feature, index) => {{
                            const itemElement = document.createElement('div');
                            itemElement.className = 'flex items-center mb-2 bg-white dark:bg-gray-800 rounded-lg p-2 ' +
                                'shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md ' +
                                'transition-shadow duration-200';
                            itemElement.dataset.index = index;

                            itemElement.innerHTML = `
                                <div class="cursor-move mr-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300
                                     transition-colors duration-200 drag-handle">
                                    <i class="fas fa-grip-vertical"></i>
                                </div>
                                <div class="flex-grow">
                                    <input type="text" value="${{html.escape(str(feature))}}"
                                           class="w-full border-none p-1 focus:outline-none focus:ring-1
                                                  focus:ring-teal-300 bg-transparent" />
                                </div>
                                <button type="button"
                                        class="ml-2 text-red-500 hover:text-red-700 dark:text-red-400
                                               dark:hover:text-red-300 transition-colors duration-200 delete-btn">
                                    <i class="fas fa-trash-alt"></i>
                                </button>
                            `;

                            itemsContainer.appendChild(itemElement);
                        }});

                        // Add event listeners for delete buttons
                        document.querySelectorAll('#{name}-items .delete-btn').forEach(button => {{
                            button.addEventListener('click', function() {{
                                const item = this.closest('[data-index]');
                                const index = parseInt(item.dataset.index);
                                features.splice(index, 1);
                                renderItems();
                                updateInput();
                            }});
                        }});
                        // Add event listeners for input changes
                        document.querySelectorAll('#{name}-items input').forEach(input => {{
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
                            // Add ARIA attributes for accessibility
                            item.setAttribute('role', 'listitem');  # noqa: F821
                            item.setAttribute(
                                'aria-label',
                                `Feature item ${parseInt(item.dataset.index) + 1}`
                            );  # noqa: F821
                            handle.setAttribute('aria-label', 'Drag handle');

                            // Mouse drag functionality
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
                                            .closest('#{name}-items [data-index]');
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

                            // Keyboard navigation
                            handle.addEventListener('keydown', function(e) {{
                                const currentIndex = parseInt(item.dataset.index);
                                let newIndex;

                                switch(e.key) {{
                                    case 'ArrowUp':
                                        e.preventDefault();
                                        newIndex = Math.max(0, currentIndex - 1);
                                        break;
                                    case 'ArrowDown':
                                        e.preventDefault();
                                        newIndex = Math.min(features.length - 1, currentIndex + 1);
                                        break;
                                    default:
                                        return;
                                }}

                                if (newIndex !== undefined && newIndex !== currentIndex) {{
                                    // Swap in the array
                                    const temp = features[currentIndex];
                                    features.splice(currentIndex, 1);
                                    features.splice(newIndex, 0, temp);
                                    // Update UI
                                    renderItems();
                                    updateInput();
                                    // Focus the moved item
                                    const newItem = itemsContainer.children[newIndex];
                                    newItem.querySelector('.drag-handle').focus();
                                }}
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
        """

    def value_from_datadict(self, data: dict, files: dict, name: str) -> list[str]:
        """
        Process the form data and return a list of non-empty strings.

        Parameters:
            data: The form data dictionary
            files: The files dictionary (unused but required by Django's Widget interface)
            name: The name of the field
        """
        json_value = data.get(name, "[]")
        try:
            value = json.loads(json_value)
            # Filter out empty strings
            if isinstance(value, list):
                return [item for item in value if item.strip()]
            return []
        except (ValueError, TypeError):
            return []
