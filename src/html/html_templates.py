"""
HTML templates for the crypto bot analysis reports
"""

def get_analysis_template(title, content, sources_section="", current_time="", expiry_time=""):
    """
    Returns the HTML template for analysis reports.

    Args:
        title: The title of the analysis
        content: The analysis content with enhanced links
        sources_section: HTML containing the sources list
        current_time: Generation time of the report
        expiry_time: Time when the report link will expire
    """
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root[data-theme="light"] {{
            --text-color: #333;
            --background-color: #f5f5f5;
            --container-bg: white;
            --heading-color: #2c3e50;
            --border-color: #3498db;
            --link-color: #3498db;
            --link-hover-color: #2980b9;
            --keypoint-bg: #ebf5fb;
            --code-bg: #f0f0f0;
            --expiry-bg: #fff3cd;
            --expiry-border: #ffc107;
            --resources-bg: #e8f4f8;
            --shadow-color: rgba(0, 0, 0, 0.1);
            --timestamp-color: #7f8c8d;
            --chart-border: #e0e0e0;
            --table-border-color: #ddd;
            --table-header-bg: #f2f2f2;
            --accent-gradient: linear-gradient(135deg, #3498db, #2980b9);
            --card-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
        }}
        
        :root[data-theme="dark"] {{
            --text-color: #e0e0e0;
            --background-color: #1a1a1a;
            --container-bg: #2d2d2d;
            --heading-color: #81b3d6;
            --border-color: #4789c0;
            --link-color: #64b5f6;
            --link-hover-color: #90caf9;
            --keypoint-bg: #1e3a5f;
            --code-bg: #252525;
            --expiry-bg: #5d4037;
            --expiry-border: #8d6e63;
            --resources-bg: #263238;
            --shadow-color: rgba(0, 0, 0, 0.3);
            --timestamp-color: #b0bec5;
            --chart-border: #444444;
            --table-border-color: #555;
            --table-header-bg: #3a3a3a;
            --accent-gradient: linear-gradient(135deg, #4789c0, #81b3d6);
            --card-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            max-width: 100%;
            margin: 0 auto;
            padding: 20px;
            background-color: var(--background-color);
            transition: background-color 0.3s ease;
        }}
        
        .container {{
            background-color: var(--container-bg);
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 0 20px var(--shadow-color);
            transition: background-color 0.3s ease, box-shadow 0.3s ease;
            width: 100%;
            max-width: 95%; /* Changed from 1200px */
            margin: 0 auto;
            box-sizing: border-box;
        }}
        
        h1 {{
            color: var(--heading-color);
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 10px;
            transition: color 0.3s ease, border-color 0.3s ease;
        }}
        
        .analysis-title {{
            color: var(--heading-color);
            font-size: 1.4em;
            font-weight: bold;
            margin-bottom: 20px;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 10px;
            transition: color 0.3s ease, border-color 0.3s ease;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: inline-block;
        }}
        
        .analysis-content {{
            margin-top: 20px;
        }}
        
        .timestamp {{
            font-size: 0.8em;
            color: var(--timestamp-color);
            margin-top: 30px;
            text-align: right;
            transition: color 0.3s ease;
        }}
        
        .key-point {{
            background-color: var(--keypoint-bg);
            border-left: 4px solid var(--border-color);
            padding: 10px 15px;
            margin: 15px 0;
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }}
        
        code {{
            background-color: var(--code-bg);
            padding: 2px 5px;
            border-radius: 3px;
            font-family: 'Consolas', monospace;
            transition: background-color 0.3s ease;
        }}
        
        .expiry-notice {{
            background-color: var(--expiry-bg);
            border-left: 4px solid var(--expiry-border);
            padding: 10px 15px;
            margin-top: 30px;
            font-size: 0.9em;
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }}
        
        a {{
            color: var(--link-color);
            text-decoration: none;
            border-bottom: 1px dotted var(--link-color);
            transition: color 0.3s ease, border-color 0.3s ease;
        }}
        
        a:hover {{
            color: var(--link-hover-color);
            border-bottom: 1px solid var(--link-hover-color);
        }}
        
        .resources {{
            background-color: var(--resources-bg);
            border-radius: 5px;
            padding: 15px;
            margin-top: 25px;
            transition: background-color 0.3s ease;
        }}
        
        .resources h4 {{
            margin-top: 0;
            color: var(--heading-color);
            transition: color 0.3s ease;
        }}
        
        .resources ul {{
            padding-left: 20px;
        }}
        
        .theme-switch {{
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: var(--container-bg);
            border: 1px solid var(--border-color);
            border-radius: 5px;
            padding: 8px 12px;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
            transition: background-color 0.3s ease, border-color 0.3s ease;
            z-index: 1000;
        }}
        
        .theme-switch:hover {{
            background-color: var(--resources-bg);
        }}
        
        .theme-switch-icon {{
            margin-right: 8px;
        }}
        
        /* Chart styling */
        .chart-section {{
            position: relative;
            margin-bottom: 30px;
            width: 100%;
        }}
        
        .market-chart {{
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            width: 100%;
            border-radius: 12px;
            box-shadow: var(--card-shadow);
            transition: box-shadow 0.3s ease, transform 0.3s ease;
            overflow: hidden;
            padding: 20px;
            margin: 20px 0;
            background-color: var(--container-bg);
        }}
        
        .market-chart:hover {{
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.3);
            transform: translateY(-2px);
        }}
        
        .market-chart h3 {{
            color: var(--heading-color);
            margin-top: 0;
            padding-bottom: 10px;
            border-bottom: 1px dashed var(--border-color);
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: inline-block;
        }}
        
        .chart-container {{
            border: 1px solid var(--chart-border);
            border-radius: 8px;
            padding: 15px;
            overflow: hidden;
            margin: 20px 0;
            background-color: var(--container-bg);
            box-shadow: 0 2px 10px var(--shadow-color);
            width: 100%;
            box-sizing: border-box;
        }}
        
        .analysis-details {{
            margin-top: 30px;
            border-radius: 12px;
            box-shadow: var(--card-shadow);
            transition: box-shadow 0.3s ease, transform 0.3s ease;
            overflow: hidden;
            padding: 20px;
            margin: 20px 0;
            background-color: var(--container-bg);
        }}
        
        .analysis-details:hover {{
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.3);
            transform: translateY(-2px);
        }}
        
        /* Chart loading styles */
        .chart-loading-container {{
            position: relative;
            min-height: 300px;
        }}
        
        .chart-loading {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: var(--background-color);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 10;
        }}
        
        .loading-spinner {{
            width: 50px;
            height: 50px;
            border: 5px solid var(--border-color);
            border-radius: 50%;
            border-top: 5px solid var(--link-color);
            animation: spin 1s linear infinite;
            margin-bottom: 15px;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        /* Table styling */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.9em;
            box-shadow: 0 2px 5px var(--shadow-color);
            overflow: hidden;
            border-radius: 5px;
        }}
        
        thead tr {{
            background-color: var(--table-header-bg);
            color: var(--heading-color);
            text-align: left;
            font-weight: bold;
        }}
        
        th, td {{
            padding: 12px 15px;
            border: 1px solid var(--table-border-color);
            text-align: left;
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }}
        
        tbody tr {{
            border-bottom: 1px solid var(--table-border-color);
        }}
        
        tbody tr:nth-of-type(even) {{
            background-color: var(--code-bg);
        }}
        
        tbody tr:last-of-type {{
            border-bottom: 2px solid var(--border-color);
        }}
        
        tbody tr:hover {{
            background-color: var(--keypoint-bg);
        }}
        
        /* Make charts responsive */
        .js-plotly-plot {{
            max-width: 100% !important;
            width: 100% !important;
        }}
        
        .js-plotly-plot .plotly {{
            width: 100% !important;
        }}
        
        .js-plotly-plot .plot-container {{
            width: 100% !important;
        }}
        
        .main-svg {{
            width: 100% !important;
        }}
        
        /* Enhanced Mobile Responsiveness */
        @media (max-width: 768px) {{
            .container {{
                padding: 15px;
            }}
            
            body {{
                padding: 10px;
                font-size: 14px;
            }}
            
            .market-chart {{
                padding: 10px;
            }}
            
            .theme-switch {{
                top: 10px;
                right: 10px;
                padding: 10px 15px;
                font-size: 12px;
            }}
            
            table {{
                display: block;
                overflow-x: auto;
                white-space: nowrap;
            }}
            
            h1 {{
                font-size: 1.8em;
            }}
            
            table {{
                font-size: 0.8em;
            }}
            
            th, td {{
                padding: 8px 10px;
            }}
        }}
        
        /* Back to top button */
        .back-to-top {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: var(--container-bg);
            color: var(--link-color);
            border-radius: 50%;
            width: 50px;
            height: 50px;
            text-align: center;
            line-height: 50px;
            font-size: 20px;
            cursor: pointer;
            opacity: 0;
            transition: opacity 0.3s ease;
            box-shadow: 0 2px 10px var(--shadow-color);
            z-index: 1000;
        }}
        
        .back-to-top.visible {{
            opacity: 0.8;
        }}
        
        .back-to-top:hover {{
            opacity: 1;
        }}
        
        /* Collapsible sections */
        .collapsible-header {{
            cursor: pointer;
            padding: 12px 15px;
            background-color: var(--keypoint-bg);
            border-radius: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 3px;
        }}
        
        .collapsible-content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease;
            background-color: var(--container-bg);
            border-radius: 0 0 6px 6px;
        }}
        
        .collapsible-content.open {{
            max-height: 2000px;
        }}
        
        :focus {{
            outline: 3px solid var(--link-color);
            outline-offset: 3px;
        }}
        
        /* High contrast mode supports */
        @media (forced-colors: active) {{
            .analysis-title, .market-chart h3 {{
                -webkit-text-fill-color: CanvasText;
            }}
            
            a:focus {{
                outline: 3px solid Highlight;
            }}
        }}
    </style>
</head>
<body>
    <button class="theme-switch" onclick="toggleTheme()" id="themeToggle" aria-label="Toggle color theme">
        <span class="theme-switch-icon" aria-hidden="true">☀️</span>
        <span>Light Mode</span>
    </button>
    
    <div class="container" role="main">
        <h1 id="analysis-title">{title}</h1>
        <div class="analysis-title" role="heading" aria-level="2">Detailed Analysis</div>
        <div class="analysis-content" role="article" aria-labelledby="analysis-title">
            {content}
        </div>
        <div role="complementary" aria-label="Sources and additional information">
            {sources_section}
        </div>
        <div class="expiry-notice">
            This analysis link on Discord will expire in 1 hour, at {expiry_time}.
        </div>
        <div class="timestamp">
            Generated on: {current_time}
        </div>
    </div>
    
    <div class="back-to-top">↑</div>
    
    <script>
        // Check for saved theme preference or default to light mode
        function getTheme() {{
            return localStorage.getItem('crypto-analysis-theme') || 'dark';
        }}
        
        // Apply the current theme
        function applyTheme(theme) {{
            document.documentElement.setAttribute('data-theme', theme);
            const themeToggle = document.getElementById('themeToggle');
            if (theme === 'dark') {{
                themeToggle.innerHTML = '<span class="theme-switch-icon" aria-hidden="true">☀️</span><span>Light Mode</span>';
            }} else {{
                themeToggle.innerHTML = '<span class="theme-switch-icon" aria-hidden="true">🌙</span><span>Dark Mode</span>';
            }}
        }}
        
        // Toggle between light and dark themes
        function toggleTheme() {{
            const currentTheme = getTheme();
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            localStorage.setItem('crypto-analysis-theme', newTheme);
            applyTheme(newTheme);
        }}
        
        // Apply theme immediately to avoid flash of unstyled content
        document.addEventListener('DOMContentLoaded', function() {{
            applyTheme(getTheme());
            
            // Back to top button
            const backToTop = document.querySelector('.back-to-top');
            window.addEventListener('scroll', function() {{
                if (window.scrollY > 300) {{
                    backToTop.classList.add('visible');
                }} else {{
                    backToTop.classList.remove('visible');
                }}
            }});
            
            backToTop.addEventListener('click', function() {{
                window.scrollTo({{
                    top: 0,
                    behavior: 'smooth'
                }});
            }});
        }});
    </script>
</body>
</html>"""

def get_error_template(error_message):
    """
    Returns a simple HTML template for displaying errors
    
    Args:
        error_message: The error message to display
    """
    return f"""<!DOCTYPE html>
<html><body><h1>Error Generating Analysis</h1>
<p>There was a problem generating the analysis: {error_message}</p>
</body></html>"""