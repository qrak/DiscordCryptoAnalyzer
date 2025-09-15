"""
Chart generator utility for creating simple interactive plots of market data.
"""
from datetime import datetime
from typing import Dict, List, Any, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class ChartGenerator:
    """Generates simple interactive charts for market data with OHLCV and RSI."""
    
    def __init__(self):
        self.default_colors = {
            'background': '#1a1a1a',
            'grid': '#333333',
            'text': '#e0e0e0',
            'candle_up': '#26a69a',
            'candle_down': '#ef5350',
            'volume': '#3370d4',
            'rsi': '#e6c700'
        }
        
    def create_ohlcv_chart(
        self,
        ohlcv: np.ndarray,
        technical_history: Optional[Dict[str, np.ndarray]] = None,
        patterns: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        pair_symbol: str = "",
        timeframe: str = "1h",
        height: int = 800,  # Increased default height for two plots
        width: int = None
    ) -> str:
        """Create an interactive chart with OHLCV, Volume, and RSI."""
        # Convert timestamps to pandas datetime for proper formatting
        timestamps = pd.to_datetime(ohlcv[:, 0], unit='ms')
        
        # Determine if RSI data is available
        has_rsi = technical_history and 'rsi' in technical_history and len(technical_history['rsi']) == len(timestamps)

        # Create subplots: 3 rows if RSI, 2 rows if no RSI
        # Row 1: Price (with secondary y-axis for right-side axis)
        # Row 2: Volume 
        # Row 3: RSI (if available)
        rows = 3 if has_rsi else 2
        if has_rsi:
            row_heights = [0.6, 0.2, 0.2]  # Price gets 60%, Volume 20%, RSI 20%
            specs = [
                [{"secondary_y": True}],   # Price row with secondary y-axis
                [{"secondary_y": False}],  # Volume row
                [{"secondary_y": False}]   # RSI row
            ]
        else:
            row_heights = [0.7, 0.3]  # Price gets 70%, Volume 30%
            specs = [
                [{"secondary_y": True}],   # Price row with secondary y-axis  
                [{"secondary_y": False}]   # Volume row
            ]

        fig = make_subplots(
            rows=rows, 
            cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03,  # Reduced spacing
            row_heights=row_heights,
            specs=specs
        )
        
        # --- Plot 1: Price Candlesticks ---
        
        # Add candlestick chart on secondary y-axis (right side)
        candle = go.Candlestick(
            x=timestamps,
            open=ohlcv[:, 1],
            high=ohlcv[:, 2],
            low=ohlcv[:, 3],
            close=ohlcv[:, 4],
            name="Price",
            increasing_line_color=self.default_colors['candle_up'],
            decreasing_line_color=self.default_colors['candle_down']
        )
        fig.add_trace(candle, row=1, col=1, secondary_y=True)
        
        # --- Plot 2: Volume ---
        
        # Add volume as a bar chart in its own subplot
        volume = go.Bar(
            x=timestamps,
            y=ohlcv[:, 5],
            name="Volume",
            marker_color=self.default_colors['volume'],
            opacity=0.6,
        )
        fig.add_trace(volume, row=2, col=1)
        
        # --- Plot 3: RSI (if available) ---
        # --- Plot 3: RSI (if available) ---
        if has_rsi:
            rsi_values = technical_history['rsi']
            
            # Add RSI line in the third row
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=rsi_values,
                name="RSI (14)",
                line=dict(color=self.default_colors['rsi'], width=1.5)
            ), row=3, col=1)
            
            # Add RSI Overbought/Oversold lines
            for level, color, dash in [(70, 'rgba(239, 83, 80, 0.7)', 'dash'), (30, 'rgba(38, 166, 154, 0.7)', 'dash')]:
                fig.add_trace(go.Scatter(
                    x=[timestamps[0], timestamps[-1]],
                    y=[level, level],
                    mode='lines',
                    line=dict(color=color, width=1, dash=dash),
                    showlegend=False,
                    hoverinfo='skip'  # Don't show hover info for these lines
                ), row=3, col=1)
            
            # Set RSI y-axis range and title
            fig.update_yaxes(title_text="RSI", range=[0, 100], row=3, col=1)

        # --- Layout Updates ---
        fig.update_layout(
            title=f"{pair_symbol} Market Analysis - {timeframe}",
            xaxis_rangeslider_visible=False,  # Hide range slider for cleaner look
            template="plotly_dark",
            height=height,
            width=width,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.01,  # Position legend slightly above the top chart
                xanchor="left",
                x=0
            ),
            font=dict(family="Arial, sans-serif", size=11, color=self.default_colors['text']),  # Adjusted font
            paper_bgcolor=self.default_colors['background'],
            plot_bgcolor=self.default_colors['background'],
            margin=dict(l=40, r=40, t=60, b=40),  # Adjusted margins
            dragmode='pan',  # Changed default drag mode to pan
            hovermode='x unified',  # Keep unified hover
            autosize=True
        )
        
        # --- Axis Configuration ---
        
        # Configure Primary Y-axis (Row 1, Left side) - Empty/Hidden for cleaner look
        fig.update_yaxes(
            showgrid=False,
            showticklabels=False,
            visible=False,
            row=1, col=1, 
            secondary_y=False
        )
        
        # Configure Price axis (Secondary Y-axis, Row 1, Right side)
        fig.update_yaxes(
            title_text="Price", 
            showgrid=True, 
            gridwidth=1, 
            gridcolor=self.default_colors['grid'], 
            zeroline=False,
            side="right",
            row=1, col=1, 
            secondary_y=True
        )
        
        # Configure Volume axis (Row 2)
        fig.update_yaxes(
            title_text="Volume", 
            showgrid=True,
            gridwidth=1,
            gridcolor=self.default_colors['grid'],
            zeroline=False,
            row=2, col=1
        )

        # Configure X-axes
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor=self.default_colors['grid'],
            zeroline=False,
            tickformat='%b %d, %H:%M',  # Slightly different date format
            tickangle=0,  # No angle for better fit with fewer labels
            showticklabels=True,  # Ensure bottom x-axis labels are visible
            row=rows, col=1  # Apply to the bottom-most x-axis
        )
        
        # Hide tick labels on the top x-axis if there are multiple rows
        if rows > 1:
            fig.update_xaxes(showticklabels=False, row=1, col=1)
        
        # Configure RSI Y-axis (Row 3, if exists)
        if has_rsi:
            fig.update_yaxes(
                title_text="RSI",
                showgrid=True,
                gridwidth=1,
                gridcolor=self.default_colors['grid'],
                zeroline=False,
                range=[0, 100],
                row=3, col=1
            )
        
        # Generate a unique ID for this chart instance 
        chart_id = f"crypto_chart_{int(datetime.now().timestamp())}"
        
        # Configure for responsiveness
        config = {
            'responsive': True,
            'displayModeBar': True,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': f'{pair_symbol}_analysis',
                'scale': 2
            }
        }
        
        # Return the figure as HTML
        fig_html = fig.to_html(
            include_plotlyjs='cdn', 
            full_html=False, 
            div_id=chart_id,
            config=config
        )

        # Add a loading state for the chart
        chart_html = f"""
        <div id="{chart_id}-container" class="chart-loading-container">
            <div class="chart-loading" id="{chart_id}-loading">
                <div class="loading-spinner"></div>
                <p>Loading market data chart...</p>
            </div>
            {fig_html}
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const chartContainer = document.getElementById('{chart_id}-container');
                const loadingElement = document.getElementById('{chart_id}-loading');
                
                // Hide loading indicator when chart is ready
                if (chartContainer && loadingElement) {{
                    // Check if Plotly chart is ready
                    const checkPlotlyReady = setInterval(function() {{
                        if (document.querySelector('#{chart_id} .plot-container')) {{
                            loadingElement.style.display = 'none';
                            clearInterval(checkPlotlyReady);
                        }}
                    }}, 100);
                    
                    // Fallback timeout - hide loading after 5 seconds regardless
                    setTimeout(function() {{
                        if (loadingElement) loadingElement.style.display = 'none';
                    }}, 5000);
                }}
            }});
        </script>
        """
        return chart_html


