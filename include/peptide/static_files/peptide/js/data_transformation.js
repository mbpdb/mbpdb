/**
 * Data Transformation Wizard - AJAX navigation and progress polling.
 */
(function() {
    'use strict';

    var currentStep = 1;
    var definedGroups = [];
    var availableColumns = [];
    var selectedColumns = [];  // columns selected for the current group being built
    var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // -----------------------------------------------------------------------
    // Drag & drop file inputs
    // -----------------------------------------------------------------------
    document.querySelectorAll('.dt-dropzone').forEach(function(zone) {
        var input = zone.querySelector('input[type="file"]');
        var dropText = zone.querySelector('.drop-text');
        var fileName = zone.querySelector('.file-name');

        function showFile(name) {
            dropText.classList.add('hidden');
            fileName.textContent = name;
            fileName.classList.remove('hidden');
        }

        input.addEventListener('change', function() {
            if (this.files.length) showFile(this.files[0].name);
            // When functional file is selected, gray out BLAST threshold section
            if (this.id === 'functional_file') {
                updateBlastThresholdState();
            }
        });

        zone.addEventListener('dragover', function(e) {
            e.preventDefault();
            zone.classList.add('dragover');
        });
        zone.addEventListener('dragleave', function() {
            zone.classList.remove('dragover');
        });
        zone.addEventListener('drop', function(e) {
            e.preventDefault();
            zone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                showFile(e.dataTransfer.files[0].name);
                if (input.id === 'functional_file') {
                    updateBlastThresholdState();
                }
            }
        });
    });

    function updateBlastThresholdState() {
        var functionalFile = document.getElementById('functional_file');
        var blastSection = document.getElementById('blast-threshold-section');
        if (!blastSection) return;
        var hasFile = functionalFile && functionalFile.files && functionalFile.files.length > 0;
        // Only toggle the visual greyed-out state — never set disabled so the
        // select value is still submitted and form validation passes.
        blastSection.classList.toggle('disabled-section', hasFile);
    }

    // Utility: AJAX helper
    function ajax(method, url, data, callback, errorCallback) {
        var xhr = new XMLHttpRequest();
        xhr.open(method, url);
        xhr.setRequestHeader('X-CSRFToken', csrfToken);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

        xhr.onload = function() {
            var resp;
            try {
                resp = JSON.parse(xhr.responseText);
            } catch(e) {
                // Server returned non-JSON — surface the raw text so user can diagnose
                var raw = xhr.responseText ? xhr.responseText.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim() : '';
                var preview = raw.substring(0, 300);
                resp = {error: 'Server returned an unexpected response (HTTP ' + xhr.status + '). ' +
                    (preview ? 'Details: ' + preview : 'Check server logs.')};
            }
            if (xhr.status >= 200 && xhr.status < 300) {
                callback(resp);
            } else {
                (errorCallback || showError)(resp.error || 'Request failed');
            }
        };
        xhr.onerror = function() {
            (errorCallback || showError)('Network error');
        };

        if (data instanceof FormData) {
            xhr.send(data);
        } else if (data) {
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.send(JSON.stringify(data));
        } else {
            xhr.send();
        }
    }

    function showError(msg) {
        var el = document.getElementById('dt-error');
        el.textContent = msg;
        el.classList.remove('hidden');
        setTimeout(function() { el.classList.add('hidden'); }, 10000);
    }

    function goToStep(step) {
        currentStep = step;
        var indicators = document.querySelectorAll('.dt-step-indicator');
        var contents = document.querySelectorAll('.dt-step-content');
        indicators.forEach(function(ind) {
            var s = parseInt(ind.getAttribute('data-step'));
            ind.classList.remove('active', 'completed');
            if (s < step) ind.classList.add('completed');
            else if (s === step) ind.classList.add('active');
        });
        contents.forEach(function(c) {
            var s = parseInt(c.getAttribute('data-step'));
            c.classList.toggle('active', s === step);
        });
    }

    // -----------------------------------------------------------------------
    // Step 1: Upload & BLAST
    // -----------------------------------------------------------------------

    document.getElementById('upload-form').addEventListener('submit', function(e) {
        e.preventDefault();
        var btn = document.getElementById('upload-btn');
        btn.disabled = true;
        btn.innerHTML = '<span class="dt-spinner"></span> Uploading...';

        var formData = new FormData(this);
        ajax('POST', 'upload/', formData, function(resp) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-upload"></i> Upload & Validate';

            var summary = '<div class="dt-alert dt-alert-success">' +
                'Loaded <strong>' + resp.rows + '</strong> rows, <strong>' + resp.columns + '</strong> columns. ' +
                'Found <strong>' + resp.sequences + '</strong> unique sequences to search.</div>';
            if (resp.has_mbpdb) {
                summary += '<div class="dt-alert dt-alert-success">' +
                    '<i class="fas fa-check-circle"></i> MBPDB file loaded: <strong>' +
                    resp.mbpdb_rows + '</strong> records. Skipping BLAST search.</div>';
            }
            if (resp.warning) {
                summary += '<div class="dt-alert dt-alert-warning">' + resp.warning + '</div>';
            }
            document.getElementById('upload-summary').innerHTML = summary;
            document.getElementById('upload-results').classList.remove('hidden');

            // If MBPDB data was uploaded, auto-fire the BLAST step (which will skip
            // immediately) so the user doesn't have to click "Search MBPDB".
            if (resp.has_mbpdb) {
                ajax('POST', 'start-blast/', null, function(blastResp) {
                    document.getElementById('blast-results').classList.remove('hidden');
                    document.getElementById('blast-summary').innerHTML =
                        '<div class="dt-alert dt-alert-info">' +
                        '<i class="fas fa-database"></i> ' + blastResp.message +
                        ' (' + blastResp.count + ' records)</div>';
                });
            }
        }, function(msg) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-upload"></i> Upload & Validate';
            showError(msg);
        });
    });

    document.getElementById('start-blast-btn').addEventListener('click', function() {
        var btn = this;
        btn.disabled = true;

        ajax('POST', 'start-blast/', null, function(resp) {
            if (resp.skipped) {
                document.getElementById('blast-results').classList.remove('hidden');
                document.getElementById('blast-summary').innerHTML =
                    '<div class="dt-alert dt-alert-info">' + resp.message +
                    ' (' + resp.count + ' rows)</div>';
                return;
            }
            document.getElementById('blast-progress').classList.remove('hidden');
            pollProgress(resp.task_id, 'blast-progress-bar', 'blast-progress-text', function() {
                ajax('GET', 'blast-results/' + resp.task_id + '/', null, function(r) {
                    document.getElementById('blast-progress').classList.add('hidden');
                    document.getElementById('blast-results').classList.remove('hidden');
                    document.getElementById('blast-summary').innerHTML =
                        '<div class="dt-alert dt-alert-success">Search complete. Found <strong>' +
                        r.count + '</strong> matches.</div>';
                });
            });
        }, function(msg) {
            btn.disabled = false;
            showError(msg);
        });
    });

    document.getElementById('skip-blast-btn').addEventListener('click', function() {
        goToStep(2);
        loadStep2();
    });

    document.getElementById('goto-step2-btn').addEventListener('click', function() {
        goToStep(2);
        loadStep2();
    });

    // -----------------------------------------------------------------------
    // Progress polling (reuses existing /check-progress/ endpoint)
    // -----------------------------------------------------------------------

    function pollProgress(taskId, barId, textId, onComplete) {
        var bar = document.getElementById(barId);
        var text = document.getElementById(textId);
        var interval = setInterval(function() {
            ajax('GET', '/check-progress/' + taskId + '/', null, function(resp) {
                var pct = resp.percent_progress || 0;
                bar.style.width = pct + '%';

                if (resp.estimated_time_remaining != null) {
                    text.textContent = Math.round(pct) + '% - ~' +
                        Math.ceil(resp.estimated_time_remaining) + 's remaining';
                } else {
                    text.textContent = Math.round(pct) + '%';
                }

                if (resp.status === 'complete') {
                    clearInterval(interval);
                    bar.style.width = '100%';
                    text.textContent = 'Complete!';
                    onComplete();
                } else if (resp.status === 'failed') {
                    clearInterval(interval);
                    text.textContent = 'Failed.';
                    showError('Task failed');
                }
            });
        }, 2000);
    }

    // -----------------------------------------------------------------------
    // Step 2: Study Variable Grouping
    // -----------------------------------------------------------------------

    function loadStep2() {
        ajax('GET', 'step2/', null, function(resp) {
            availableColumns = resp.columns || [];
            selectedColumns = [];
            renderColumnPanels('');
        });
    }

    // Render the dual-panel column selector
    function renderColumnPanels(filter) {
        var f = (filter || '').toLowerCase();
        var availList = document.getElementById('column-available-list');
        var selList = document.getElementById('column-selected-list');
        var availCount = document.getElementById('avail-count');
        var selCount = document.getElementById('selected-count');

        // Available panel: columns not yet selected, filtered by search
        availList.innerHTML = '';
        var shown = 0;
        availableColumns.forEach(function(col) {
            if (selectedColumns.indexOf(col) !== -1) return;  // already selected
            if (f && col.toLowerCase().indexOf(f) === -1) return;
            shown++;
            var div = document.createElement('div');
            div.className = 'dt-col-item';
            div.title = col;
            div.textContent = col;
            div.addEventListener('click', function() {
                if (selectedColumns.indexOf(col) === -1) {
                    selectedColumns.push(col);
                    renderColumnPanels(document.getElementById('column-search').value);
                }
            });
            availList.appendChild(div);
        });
        if (!shown) {
            availList.innerHTML = '<div class="dt-col-empty">No columns available</div>';
        }
        availCount.textContent = '(' + shown + ')';

        // Selected panel
        selList.innerHTML = '';
        if (!selectedColumns.length) {
            selList.innerHTML = '<div class="dt-col-empty">Click columns to add</div>';
        } else {
            selectedColumns.forEach(function(col) {
                var div = document.createElement('div');
                div.className = 'dt-col-item selected-item';
                div.title = col;
                var txt = document.createElement('span');
                txt.textContent = col;
                txt.style.overflow = 'hidden';
                txt.style.textOverflow = 'ellipsis';
                var rm = document.createElement('span');
                rm.className = 'dt-col-remove';
                rm.textContent = '×';
                rm.title = 'Remove';
                rm.addEventListener('click', function(e) {
                    e.stopPropagation();
                    var idx = selectedColumns.indexOf(col);
                    if (idx !== -1) selectedColumns.splice(idx, 1);
                    renderColumnPanels(document.getElementById('column-search').value);
                });
                div.appendChild(txt);
                div.appendChild(rm);
                selList.appendChild(div);
            });
        }
        selCount.textContent = '(' + selectedColumns.length + ')';
    }

    document.getElementById('column-search').addEventListener('input', function() {
        renderColumnPanels(this.value);
    });

    document.getElementById('upload-group-json-btn').addEventListener('click', function() {
        document.getElementById('group-json-input').click();
    });

    document.getElementById('group-json-input').addEventListener('change', function() {
        if (!this.files.length) return;
        var formData = new FormData();
        formData.append('group_file', this.files[0]);
        ajax('POST', 'upload-groups/', formData, function(resp) {
            definedGroups = [];
            Object.keys(resp.groups).forEach(function(name) {
                definedGroups.push({name: name, columns: resp.groups[name] || []});
            });
            renderGroups();
            document.getElementById('submit-groups-btn').disabled = false;
            // Note: do NOT auto-advance — let the user review and continue manually
        });
    });

    document.getElementById('add-group-btn').addEventListener('click', function() {
        var name = document.getElementById('group-name-input').value.trim();
        if (!name) { showError('Please enter a group name'); return; }
        if (!selectedColumns.length) { showError('Please select at least one column'); return; }

        definedGroups.push({name: name, columns: selectedColumns.slice()});
        renderGroups();
        document.getElementById('group-name-input').value = '';
        selectedColumns = [];
        renderColumnPanels(document.getElementById('column-search').value);
        document.getElementById('submit-groups-btn').disabled = false;
    });

    function renderGroups() {
        var list = document.getElementById('groups-list');
        list.innerHTML = '';
        if (!definedGroups.length) {
            document.getElementById('defined-groups').classList.add('hidden');
            return;
        }
        document.getElementById('defined-groups').classList.remove('hidden');
        definedGroups.forEach(function(g, i) {
            var div = document.createElement('div');
            div.className = 'dt-group-item';
            div.innerHTML = '<span><strong>' + g.name + '</strong> (' + g.columns.length + ' columns)</span>' +
                '<span class="remove-group" data-idx="' + i + '"><i class="fas fa-times"></i></span>';
            list.appendChild(div);
        });
        list.querySelectorAll('.remove-group').forEach(function(el) {
            el.addEventListener('click', function() {
                definedGroups.splice(parseInt(this.getAttribute('data-idx')), 1);
                renderGroups();
                if (!definedGroups.length) document.getElementById('submit-groups-btn').disabled = true;
            });
        });
    }

    document.getElementById('reset-groups-btn').addEventListener('click', function() {
        definedGroups = [];
        selectedColumns = [];
        document.getElementById('group-name-input').value = '';
        document.getElementById('column-search').value = '';
        renderGroups();
        renderColumnPanels('');
        document.getElementById('submit-groups-btn').disabled = true;
    });

    document.getElementById('back-to-step1-btn').addEventListener('click', function() {
        goToStep(1);
    });

    document.getElementById('submit-groups-btn').addEventListener('click', function() {
        var btn = this;
        btn.disabled = true;
        ajax('POST', 'submit-groups/', {groups: definedGroups}, function() {
            goToStep(3);
            loadStep3();
        }, function(msg) { btn.disabled = false; showError(msg); });
    });

    document.getElementById('skip-groups-btn').addEventListener('click', function() {
        var btn = this;
        btn.disabled = true;
        ajax('POST', 'skip-groups/', {columns: selectedColumns}, function() {
            btn.disabled = false;
            goToStep(3);
            loadStep3();
        }, function(msg) { btn.disabled = false; showError(msg); });
    });

    // -----------------------------------------------------------------------
    // Step 3: Protein Mapping
    // -----------------------------------------------------------------------

    function loadStep3() {
        ajax('GET', 'step3/', null, function(resp) {
            renderStep3Info(resp);
        });
    }

    function renderStep3Info(resp) {
        var info = document.getElementById('protein-info');
        var html = '';

        // Known proteins summary
        if (resp.known_protein_count > 0) {
            html += '<div class="dt-alert dt-alert-success" style="margin-bottom: 8px;">' +
                '<strong>' + resp.known_protein_count + '</strong> protein(s) mapped.</div>';
            if (resp.known_proteins && resp.known_proteins.length > 0) {
                html += '<div style="max-height: 120px; overflow-y: auto; font-size: 0.82rem; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 6px 10px; margin-bottom: 8px;">';
                resp.known_proteins.forEach(function(p) {
                    html += '<span style="display:inline-block; margin-right:16px; margin-bottom:2px;">' +
                        '<strong>' + escHtml(p.id) + '</strong>' +
                        (p.name ? ' — ' + escHtml(p.name.split(' ').slice(0,4).join(' ')) : '') +
                        (p.species ? ' <em>(' + escHtml(p.species) + ')</em>' : '') + '</span>';
                });
                if (resp.known_protein_count > 50) html += '…';
                html += '</div>';
            }
        }

        // Proteins not yet looked up — user can fetch these
        if (resp.missing_protein_count > 0) {
            html += '<div class="dt-alert dt-alert-warning" style="margin-bottom:4px;">' +
                '<strong>' + resp.missing_protein_count + '</strong> protein(s) not yet identified — ' +
                'click <strong>Fetch from UniProt</strong> to look them up.</div>';
            if (resp.missing_ids && resp.missing_ids.length > 0) {
                html += '<div style="max-height: 80px; overflow-y: auto; font-size: 0.82rem; ' +
                    'color: #666; background:#fff8e1; border:1px solid #ffe082; border-radius:4px; ' +
                    'padding:4px 8px; margin-bottom:8px;">' +
                    resp.missing_ids.map(escHtml).join(', ') +
                    (resp.missing_protein_count > 50 ? ', …' : '') + '</div>';
            }
        }

        // Proteins already tried in UniProt but could not be resolved
        if (resp.unresolvable_count > 0) {
            html += '<div class="dt-alert" style="background:#f5f5f5; border:1px solid #ccc; ' +
                'color:#666; margin-bottom:4px;">' +
                '<i class="fas fa-exclamation-circle" style="margin-right:4px;"></i>' +
                '<strong>' + resp.unresolvable_count + '</strong> protein ID(s) could not be found in UniProt ' +
                '(non-standard format or retired accession). These will remain unmapped.</div>';
            if (resp.unresolvable_ids && resp.unresolvable_ids.length > 0) {
                html += '<div style="max-height: 80px; overflow-y: auto; font-size: 0.82rem; ' +
                    'color: #888; background:#fafafa; border:1px solid #e0e0e0; border-radius:4px; ' +
                    'padding:4px 8px; margin-bottom:8px; text-decoration:line-through;">' +
                    resp.unresolvable_ids.map(escHtml).join(', ') +
                    (resp.unresolvable_count > 50 ? ', …' : '') + '</div>';
            }
        }

        if (resp.missing_protein_count === 0 && resp.unresolvable_count === 0) {
            if (resp.known_protein_count === 0) {
                html += '<div class="dt-alert dt-alert-info">No protein identifiers found in the data. ' +
                    'Ensure your file has a protein/accession column.</div>';
            } else {
                html += '<div class="dt-alert dt-alert-success">All proteins are mapped.</div>';
            }
        }

        info.innerHTML = html;

        // Show/hide the fetch button based on whether there's anything left to fetch
        var fetchBtn = document.getElementById('fetch-uniprot-btn');
        if (fetchBtn) {
            if (resp.missing_protein_count > 0) {
                fetchBtn.classList.remove('hidden');
                fetchBtn.innerHTML = '<i class="fas fa-download"></i> Fetch from UniProt' +
                    ' (' + resp.missing_protein_count + ')';
            } else {
                fetchBtn.classList.add('hidden');
            }
        }

        if (resp.has_combinations && resp.combinations.length > 0) {
            document.getElementById('protein-combinations').classList.remove('hidden');
            renderCombinations(resp.combinations);
        } else {
            document.getElementById('protein-combinations').classList.add('hidden');
        }
    }

    function renderCombinations(combos) {
        var list = document.getElementById('combinations-list');
        list.innerHTML = '';
        combos.forEach(function(combo, idx) {
            var div = document.createElement('div');
            div.className = 'dt-combo-row';
            var html = '<strong>' + combo.combo + '</strong> (' + combo.occurrences + ' rows)<br>';

            // Option: Leave As Is
            html += '<label style="display: block; margin: 4px 0;">' +
                '<input type="radio" name="combo_' + idx + '" value="__ASIS__" checked> ' +
                'Leave as is (keep combined ID)</label>';

            // Option: each individual protein ID
            combo.proteins.forEach(function(p) {
                html += '<label style="display: block; margin: 4px 0;">' +
                    '<input type="radio" name="combo_' + idx + '" value="' + p.id + '"> ' +
                    p.id + (p.name ? ' — ' + p.name : '') +
                    (p.species ? ' (' + p.species + ')' : '') + '</label>';
            });

            // Option: Custom ID
            html += '<label style="display: block; margin: 4px 0;">' +
                '<input type="radio" name="combo_' + idx + '" value="__CUSTOM__"> ' +
                'Custom ID: <input type="text" id="custom_' + idx + '" ' +
                'placeholder="Enter protein ID" style="margin-left: 6px; width: 200px; display: inline;" ' +
                'onfocus="this.parentElement.querySelector(\'input[type=radio]\').checked=true;"></label>';

            div.innerHTML = html;
            list.appendChild(div);
        });
    }

    document.getElementById('back-to-step2-btn').addEventListener('click', function() {
        goToStep(2);
        // Re-render column panel in case columns need to be shown again
        renderColumnPanels(document.getElementById('column-search').value);
    });

    document.getElementById('fetch-uniprot-btn').addEventListener('click', function() {
        var btn = this;
        btn.disabled = true;

        function afterFetch(savedCount, taskId) {
            // Persist any fetched results then fully refresh the protein panel.
            // Pass task_id explicitly so the server doesn't have to rely on session state.
            ajax('POST', 'save-uniprot/', {task_id: taskId || null}, function(saveResp) {
                var n = (saveResp && saveResp.saved) ? saveResp.saved : (savedCount || 0);
                var fetchedProteins = (saveResp && saveResp.proteins) ? saveResp.proteins : [];
                ajax('GET', 'step3/', null, function(r) {
                    renderStep3Info(r);
                    if (n > 0) {
                        var msg = '<div class="dt-alert dt-alert-success" style="margin-bottom:8px;">' +
                            '<i class="fas fa-check-circle"></i> UniProt identified <strong>' +
                            n + '</strong> protein(s). Protein map updated.';
                        if (fetchedProteins.length > 0) {
                            msg += '<div style="margin-top:6px; font-size:0.85rem;">';
                            fetchedProteins.forEach(function(p) {
                                msg += '<span style="display:inline-block; margin-right:16px; margin-bottom:2px;">' +
                                    '<strong>' + escHtml(p.id) + '</strong>' +
                                    (p.name ? ' — ' + escHtml(p.name) : '') +
                                    (p.species ? ' <em>(' + escHtml(p.species) + ')</em>' : '') +
                                    '</span>';
                            });
                            msg += '</div>';
                        }
                        msg += '</div>';
                        document.getElementById('protein-info').insertAdjacentHTML('afterbegin', msg);
                    }
                    btn.disabled = false;
                });
            }, function() {
                ajax('GET', 'step3/', null, function(r) { renderStep3Info(r); });
                btn.disabled = false;
            });
        }

        ajax('POST', 'start-uniprot/', null, function(resp) {
            if (resp.skipped) {
                // No missing proteins — still refresh the panel in case a previous
                // fetch left results that haven't been rendered yet
                afterFetch(0, null);
                return;
            }
            var taskId = resp.task_id;
            document.getElementById('uniprot-progress').classList.remove('hidden');
            pollProgress(taskId, 'uniprot-progress-bar', 'uniprot-progress-text', function() {
                document.getElementById('uniprot-progress').classList.add('hidden');
                afterFetch(resp.count, taskId);
            });
        }, function(msg) { btn.disabled = false; showError(msg); });
    });

    document.getElementById('submit-proteins-btn').addEventListener('click', function() {
        var decisions = {};
        document.querySelectorAll('#combinations-list .dt-combo-row').forEach(function(row, idx) {
            var checked = row.querySelector('input[name="combo_' + idx + '"]:checked');
            if (checked) {
                var combo = row.querySelector('strong').textContent;
                var val = checked.value;
                if (val === '__ASIS__') {
                    decisions[combo] = {action: 'ASIS'};
                } else if (val === '__CUSTOM__') {
                    var customInput = row.querySelector('#custom_' + idx);
                    decisions[combo] = {action: 'CUSTOM', protein_id: customInput ? customInput.value.trim() : ''};
                } else {
                    decisions[combo] = {action: 'NEW', protein_id: val};
                }
            }
        });
        ajax('POST', 'submit-proteins/', {decisions: decisions}, function() {
            goToStep(4);
        });
    });

    document.getElementById('skip-proteins-btn').addEventListener('click', function() {
        ajax('POST', 'skip-proteins/', null, function() {
            goToStep(4);
        });
    });

    // -----------------------------------------------------------------------
    // Step 4: Process & Export
    // -----------------------------------------------------------------------

    document.getElementById('back-to-step3-btn').addEventListener('click', function() {
        goToStep(3);
        loadStep3();
    });

    document.getElementById('process-btn').addEventListener('click', function() {
        var btn = this;
        btn.disabled = true;
        document.getElementById('process-progress').classList.remove('hidden');

        ajax('POST', 'process/', null, function(resp) {
            btn.disabled = false;
            document.getElementById('process-progress').classList.add('hidden');
            document.getElementById('export-section').classList.remove('hidden');

            var hasFunction = resp.exports && resp.exports.summed_function;
            var hasGroups  = resp.exports && resp.exports.group_definitions;
            var summaryHtml = '<div class="dt-alert dt-alert-success">Processing complete. ' +
                'Result: <strong>' + resp.rows + '</strong> rows, <strong>' +
                resp.columns + '</strong> columns.</div>' +
                '<p style="color:#555; font-size:0.9rem; margin:8px 0 0 0;">' +
                'Your peptidomic data has been merged with MBPDB bioactive peptide annotations.' +
                (hasGroups ? ' Group abundance averages have been calculated for each experimental condition.' : '') +
                ' Protein identifications have been enriched from the protein database.' +
                (hasFunction ? ' Bioactive function annotations are included from the MBPDB database.' : '') +
                ' Use the exports below to explore protein-level abundance, functional distributions' +
                (hasGroups ? ', and group correlations' : '') +
                ' derived from your merged dataset.</p>';
            document.getElementById('process-summary').innerHTML = summaryHtml;

            renderExportButtons(resp.exports);
        }, function(msg) {
            btn.disabled = false;
            document.getElementById('process-progress').classList.add('hidden');
            showError(msg);
        });
    });

    var currentViewerSheets = [];

    function renderExportButtons(exports) {
        var container = document.getElementById('export-buttons');
        container.innerHTML = '';

        var items = [
            {key: 'mbpdb_results', icon: 'fa-database', label: 'MBPDB Results',
                desc: 'Peptides matched against the MBPDB database with biological function annotations (TSV)'},
            {key: 'group_definitions', icon: 'fa-layer-group', label: 'Group Definitions',
                desc: 'Categorical variable definitions mapping sample columns to experimental groups (JSON)'},
            {key: 'merged_dataset', icon: 'fa-table', label: 'Merged Dataset',
                desc: 'Complete processed dataset with all peptides, proteins, functions, and group averages (CSV)'},
            {key: 'sequence_list', icon: 'fa-list', label: 'Sequence List',
                desc: 'Unique peptide sequences detected in each study group (CSV)'},
            {key: 'summed_peptide', icon: 'fa-chart-bar', label: 'Summed Peptide Results',
                desc: 'Total absorbance and unique peptide count per group with replicate details and SEM (XLSX)'},
            {key: 'protein_analysis', icon: 'fa-dna', label: 'Protein Analysis',
                desc: 'Absorbance and peptide count by protein across groups with relative percentages — 4 sheets: absorbance absolute/relative, count absolute/relative (XLSX)'},
            {key: 'summed_function', icon: 'fa-flask', label: 'Summed Functional Data',
                desc: 'Bioactive function breakdown by absorbance and peptide count across groups — 5 sheets: combined, absorbance absolute/relative, count absolute/relative (XLSX)'},
            {key: 'group_correlation', icon: 'fa-chart-line', label: 'Sample-to-Sample Correlations',
                desc: 'Pearson or Spearman correlations between study groups (cross-group comparison) (XLSX)'},
            {key: 'replicate_correlation', icon: 'fa-chart-area', label: 'Replicate Correlations',
                desc: 'Pearson or Spearman correlations between technical replicates within each group (XLSX)'},
        ];

        items.forEach(function(item) {
            var enabled = exports[item.key];
            var row = document.createElement('div');
            row.className = 'dt-export-row' + (enabled ? '' : ' disabled');

            var lbl = document.createElement('div');
            lbl.className = 'dt-export-label';
            lbl.innerHTML = '<div class="dt-export-label-main">' +
                '<i class="fas ' + item.icon + '"></i> ' + item.label + '</div>' +
                (item.desc ? '<div class="dt-export-desc">' + item.desc + '</div>' : '');
            row.appendChild(lbl);

            if (enabled) {
                var actions = document.createElement('div');
                actions.className = 'dt-export-actions';

                var viewBtn = document.createElement('button');
                viewBtn.className = 'dt-export-view-btn';
                viewBtn.innerHTML = '<i class="fas fa-eye"></i> View';
                (function(key, label) {
                    viewBtn.addEventListener('click', function() { viewExport(key, label); });
                })(item.key, item.label);
                actions.appendChild(viewBtn);

                var dlBtn = document.createElement('button');
                dlBtn.className = 'dt-export-dl-btn';
                dlBtn.innerHTML = '<i class="fas fa-download"></i> Download';
                (function(key) {
                    dlBtn.addEventListener('click', function() { downloadExport(key); });
                })(item.key);
                actions.appendChild(dlBtn);

                row.appendChild(actions);
            }
            container.appendChild(row);
        });
    }

    function downloadExport(type) {
        var corrType = document.getElementById('correlation-type').value;
        var logTrans = document.getElementById('log-transform').checked;
        var url = 'download/' + type + '/?correlation_type=' + corrType +
            '&log_transform=' + logTrans;
        var iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = url;
        document.body.appendChild(iframe);
        setTimeout(function() { document.body.removeChild(iframe); }, 30000);
    }

    function viewExport(type, label) {
        var corrType = document.getElementById('correlation-type').value;
        var logTrans = document.getElementById('log-transform').checked;
        var url = 'view/' + type + '/?correlation_type=' + corrType +
            '&log_transform=' + logTrans;

        var panel = document.getElementById('dt-viewer-panel');
        var content = document.getElementById('dt-viewer-content');
        var wrap = document.getElementById('dt-viewer-wrap');
        document.getElementById('dt-viewer-title').textContent = label;
        document.getElementById('dt-viewer-tabs').innerHTML = '';
        document.getElementById('dt-viewer-info').textContent = '';
        content.innerHTML = '<div style="padding: 20px; text-align: center;"><span class="dt-spinner"></span> Loading...</div>';
        panel.classList.remove('hidden');
        panel.scrollIntoView({behavior: 'smooth', block: 'nearest'});

        ajax('GET', url, null, function(resp) {
            currentViewerSheets = resp.sheets || [];
            renderViewerSheet(0);
        }, function(msg) {
            content.innerHTML = '<div class="dt-alert dt-alert-danger" style="margin: 8px;">' + msg + '</div>';
        });
    }

    function renderViewerSheet(idx) {
        var sheets = currentViewerSheets;
        var tabsEl = document.getElementById('dt-viewer-tabs');
        var content = document.getElementById('dt-viewer-content');
        var info = document.getElementById('dt-viewer-info');

        // Render tabs if multiple sheets
        tabsEl.innerHTML = '';
        if (sheets.length > 1) {
            sheets.forEach(function(sheet, i) {
                var tab = document.createElement('div');
                tab.className = 'dt-viewer-tab' + (i === idx ? ' active' : '');
                tab.textContent = sheet.name;
                (function(i) {
                    tab.addEventListener('click', function() { renderViewerSheet(i); });
                })(i);
                tabsEl.appendChild(tab);
            });
        }

        var sheet = sheets[idx];
        if (!sheet) {
            content.innerHTML = '<div class="dt-alert dt-alert-info" style="margin: 8px;">No data</div>';
            return;
        }

        // Build table HTML
        var html = '<table class="dt-viewer-table"><thead><tr>';
        sheet.columns.forEach(function(col) {
            html += '<th>' + escHtml(String(col)) + '</th>';
        });
        html += '</tr></thead><tbody>';
        sheet.rows.forEach(function(row) {
            html += '<tr>';
            row.forEach(function(cell) {
                var val;
                if (cell === null || cell === undefined) {
                    val = '';
                } else if (typeof cell === 'number' && isFinite(cell)) {
                    var abs = Math.abs(cell);
                    if (abs >= 10000 || (cell !== 0 && abs < 0.001)) {
                        // Very large or very small — scientific notation
                        val = cell.toExponential(2);
                    } else if (cell % 1 === 0) {
                        // Whole number — no decimal places
                        val = String(Math.round(cell));
                    } else {
                        // Fractional (e.g. percentage) — max 2 decimal places
                        val = parseFloat(cell.toFixed(2)).toString();
                    }
                } else {
                    val = String(cell);
                }
                html += '<td title="' + escHtml(val) + '">' + escHtml(val.length > 80 ? val.substring(0, 80) + '…' : val) + '</td>';
            });
            html += '</tr>';
        });
        html += '</tbody></table>';
        content.innerHTML = html;

        var infoText = sheet.total_rows + ' row' + (sheet.total_rows !== 1 ? 's' : '');
        if (sheet.truncated) {
            infoText += ' — showing first ' + sheet.rows.length + ' rows';
        }
        infoText += ', ' + sheet.columns.length + ' column' + (sheet.columns.length !== 1 ? 's' : '');
        info.textContent = infoText;
    }

    function escHtml(str) {
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    document.getElementById('dt-viewer-close-btn').addEventListener('click', function() {
        document.getElementById('dt-viewer-panel').classList.add('hidden');
    });

    document.getElementById('start-over-btn').addEventListener('click', function() {
        if (!confirm('This will clear all data. Continue?')) return;
        ajax('POST', 'cleanup/', null, function() {
            location.reload();
        });
    });

})();
