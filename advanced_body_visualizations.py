# Advanced Body Content Visualizations
# Comprehensive visualizations for body content analysis

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, Any, List, Optional

def create_body_analysis_visualizations(df: pd.DataFrame, analysis: Dict[str, Any]) -> Dict[str, go.Figure]:
    """Create comprehensive visualizations for body content analysis"""
    
    charts = {}
    
    try:
        # 1. Browser Success Rate Heatmap
        if 'browser_family' in df.columns and 'ip_country' in df.columns:
            charts['browser_geo_heatmap'] = _create_browser_geo_heatmap(df)
        
        # 2. Transaction Speed vs Success Analysis
        if 'processing_time' in df.columns:
            charts['speed_success_analysis'] = _create_speed_success_analysis(df)
        
        # 3. Synthetic Data Risk Distribution
        if 'synthetic_score' in df.columns:
            charts['synthetic_risk_distribution'] = _create_synthetic_risk_distribution(df)
        
        # 4. Geographic Mismatch Analysis
        if 'geo_mismatch' in df.columns:
            charts['geographic_mismatch_analysis'] = _create_geographic_mismatch_analysis(df)
        
        # 5. Time vs Speed vs Success 3D Plot
        if all(col in df.columns for col in ['created_at', 'processing_time', 'is_successful']):
            charts['time_speed_success_3d'] = _create_time_speed_success_3d(df)
        
        # 6. Combined Risk Score Analysis
        if 'combined_risk_score' in df.columns:
            charts['combined_risk_analysis'] = _create_combined_risk_analysis(df)
        
        # 7. Hidden Dependencies Network
        if 'factor_correlations' in analysis.get('hidden_dependencies', {}):
            charts['factor_correlations'] = _create_factor_correlations_heatmap(analysis['hidden_dependencies']['factor_correlations'])
        
        # 8. Suspicious Pattern Detection
        charts['suspicious_patterns'] = _create_suspicious_patterns_chart(df)
        
    except Exception as e:
        print(f"Error creating body analysis visualizations: {e}")
    
    return charts

def _create_browser_geo_heatmap(df: pd.DataFrame) -> go.Figure:
    """Create browser vs geographic success rate heatmap"""
    
    # Prepare data for heatmap
    browser_geo_success = df.groupby(['browser_family', 'ip_country'])['is_successful'].mean().unstack(fill_value=0)
    
    fig = go.Figure(data=go.Heatmap(
        z=browser_geo_success.values,
        x=browser_geo_success.columns,
        y=browser_geo_success.index,
        colorscale='RdYlGn',
        zmid=0.5,
        text=np.round(browser_geo_success.values, 3),
        texttemplate="%{text}",
        textfont={"size": 10}
    ))
    
    fig.update_layout(
        title="Browser Success Rate by Country",
        xaxis_title="IP Country",
        yaxis_title="Browser Family",
        height=600,
        xaxis={'side': 'bottom'}
    )
    
    return fig

def _create_speed_success_analysis(df: pd.DataFrame) -> go.Figure:
    """Create comprehensive speed vs success analysis"""
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Speed vs Success Rate', 'Speed Distribution by Success', 
                       'Hourly Speed Patterns', 'Speed Category Success'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # 1. Speed vs Success Rate
    speed_bins = pd.cut(df['processing_time'], bins=20)
    speed_success = df.groupby(speed_bins)['is_successful'].agg(['mean', 'count'])
    
    fig.add_trace(
        go.Scatter(
            x=speed_success.index.astype(str),
            y=speed_success['mean'],
            mode='lines+markers',
            name='Success Rate',
            line=dict(color='blue', width=2)
        ),
        row=1, col=1
    )
    
    # 2. Speed Distribution by Success
    successful_speed = df[df['is_successful'] == True]['processing_time']
    failed_speed = df[df['is_successful'] == False]['processing_time']
    
    fig.add_trace(
        go.Histogram(x=successful_speed, name='Successful', opacity=0.7, nbinsx=30),
        row=1, col=2
    )
    
    fig.add_trace(
        go.Histogram(x=failed_speed, name='Failed', opacity=0.7, nbinsx=30),
        row=1, col=2
    )
    
    # 3. Hourly Speed Patterns
    if 'hour' in df.columns:
        hourly_speed = df.groupby('hour')['processing_time'].mean()
        fig.add_trace(
            go.Bar(x=hourly_speed.index, y=hourly_speed.values, name='Avg Speed'),
            row=2, col=1
        )
    
    # 4. Speed Category Success
    if 'speed_category' in df.columns:
        speed_cat_success = df.groupby('speed_category')['is_successful'].mean()
        fig.add_trace(
            go.Bar(x=speed_cat_success.index, y=speed_cat_success.values, name='Success Rate'),
            row=2, col=2
        )
    
    fig.update_layout(height=800, title_text="Transaction Speed Analysis")
    fig.update_xaxes(title_text="Processing Time (seconds)", row=1, col=1)
    fig.update_yaxes(title_text="Success Rate", row=1, col=1)
    fig.update_xaxes(title_text="Processing Time (seconds)", row=1, col=2)
    fig.update_yaxes(title_text="Frequency", row=1, col=2)
    fig.update_xaxes(title_text="Hour of Day", row=2, col=1)
    fig.update_yaxes(title_text="Average Processing Time", row=2, col=1)
    fig.update_xaxes(title_text="Speed Category", row=2, col=2)
    fig.update_yaxes(title_text="Success Rate", row=2, col=2)
    
    return fig

def _create_synthetic_risk_distribution(df: pd.DataFrame) -> go.Figure:
    """Create synthetic risk score distribution analysis"""
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Synthetic Risk Distribution', 'Risk vs Success Rate',
                       'High Risk Transactions', 'Risk Score by Browser'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # 1. Risk Distribution
    fig.add_trace(
        go.Histogram(x=df['synthetic_score'], nbinsx=30, name='Risk Distribution'),
        row=1, col=1
    )
    
    # 2. Risk vs Success
    risk_bins = pd.cut(df['synthetic_score'], bins=10)
    risk_success = df.groupby(risk_bins)['is_successful'].agg(['mean', 'count'])
    
    fig.add_trace(
        go.Scatter(
            x=risk_success.index.astype(str),
            y=risk_success['mean'],
            mode='lines+markers',
            name='Success Rate',
            line=dict(color='red', width=2)
        ),
        row=1, col=2
    )
    
    # 3. High Risk Transactions
    high_risk = df[df['synthetic_score'] > 3.0]
    if len(high_risk) > 0:
        fig.add_trace(
            go.Scatter(
                x=high_risk['synthetic_score'],
                y=high_risk['amount'] if 'amount' in high_risk.columns else high_risk.index,
                mode='markers',
                name='High Risk',
                marker=dict(color='red', size=8, opacity=0.7)
            ),
            row=2, col=1
        )
    
    # 4. Risk by Browser
    if 'browser_family' in df.columns:
        browser_risk = df.groupby('browser_family')['synthetic_score'].mean().sort_values(ascending=False)
        fig.add_trace(
            go.Bar(x=browser_risk.index, y=browser_risk.values, name='Avg Risk'),
            row=2, col=2
        )
    
    fig.update_layout(height=800, title_text="Synthetic Data Risk Analysis")
    fig.update_xaxes(title_text="Synthetic Risk Score", row=1, col=1)
    fig.update_yaxes(title_text="Frequency", row=1, col=1)
    fig.update_xaxes(title_text="Risk Bins", row=1, col=2)
    fig.update_yaxes(title_text="Success Rate", row=1, col=2)
    fig.update_xaxes(title_text="Risk Score", row=2, col=1)
    fig.update_yaxes(title_text="Amount", row=2, col=1)
    fig.update_xaxes(title_text="Browser Family", row=2, col=2)
    fig.update_yaxes(title_text="Average Risk Score", row=2, col=2)
    
    return fig

def _create_geographic_mismatch_analysis(df: pd.DataFrame) -> go.Figure:
    """Create geographic mismatch analysis visualization"""
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Geographic Mismatch Impact', 'Country Mismatch Patterns',
                       'ASN Analysis for Mismatches', 'Mismatch by Amount'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # 1. Mismatch Impact
    if 'geo_mismatch' in df.columns:
        mismatch_success = df.groupby('geo_mismatch')['is_successful'].agg(['mean', 'count'])
        
        fig.add_trace(
            go.Bar(
                x=['No Mismatch', 'Geographic Mismatch'],
                y=mismatch_success['mean'],
                name='Success Rate',
                text=mismatch_success['count'],
                textposition='auto'
            ),
            row=1, col=1
        )
    
    # 2. Country Mismatch Patterns
    if all(col in df.columns for col in ['billing_country', 'ip_country']):
        country_mismatch = df[df['billing_country'] != df['ip_country']].groupby(['billing_country', 'ip_country']).size().sort_values(ascending=False).head(20)
        
        fig.add_trace(
            go.Bar(
                x=[f"{billing} → {ip}" for billing, ip in country_mismatch.index],
                y=country_mismatch.values,
                name='Mismatch Count',
                orientation='h'
            ),
            row=1, col=2
        )
    
    # 3. ASN Analysis
    if 'ip_asn' in df.columns and 'geo_mismatch' in df.columns:
        asn_mismatch = df[df['geo_mismatch'] == True].groupby('ip_asn').size().sort_values(ascending=False).head(15)
        
        fig.add_trace(
            go.Bar(
                x=asn_mismatch.index,
                y=asn_mismatch.values,
                name='Mismatch Count by ASN'
            ),
            row=2, col=1
        )
    
    # 4. Mismatch by Amount
    if all(col in df.columns for col in ['geo_mismatch', 'amount']):
        amount_bins = pd.cut(df['amount'], bins=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
        amount_mismatch = df.groupby([amount_bins, 'geo_mismatch'])['is_successful'].mean().unstack(fill_value=0)
        
        for col in amount_mismatch.columns:
            fig.add_trace(
                go.Bar(
                    x=amount_mismatch.index,
                    y=amount_mismatch[col],
                    name=f'Mismatch: {col}'
                ),
                row=2, col=2
            )
    
    fig.update_layout(height=800, title_text="Geographic Mismatch Analysis")
    fig.update_xaxes(title_text="Geographic Status", row=1, col=1)
    fig.update_yaxes(title_text="Success Rate", row=1, col=1)
    fig.update_xaxes(title_text="Country Mismatch Patterns", row=1, col=2)
    fig.update_yaxes(title_text="Transaction Count", row=1, col=2)
    fig.update_xaxes(title_text="ASN", row=2, col=1)
    fig.update_yaxes(title_text="Mismatch Count", row=2, col=1)
    fig.update_xaxes(title_text="Amount Range", row=2, col=2)
    fig.update_yaxes(title_text="Success Rate", row=2, col=2)
    
    return fig

def _create_time_speed_success_3d(df: pd.DataFrame) -> go.Figure:
    """Create 3D plot of time vs speed vs success"""
    
    df['hour'] = df['created_at'].dt.hour
    
    fig = go.Figure(data=go.Scatter3d(
        x=df['hour'],
        y=df['processing_time'],
        z=df['is_successful'],
        mode='markers',
        marker=dict(
            size=5,
            color=df['is_successful'],
            colorscale='Viridis',
            opacity=0.7
        ),
        text=df['id'].astype(str)
    ))
    
    fig.update_layout(
        title="3D Analysis: Time vs Speed vs Success",
        scene=dict(
            xaxis_title="Hour of Day",
            yaxis_title="Processing Time (seconds)",
            zaxis_title="Success (0=Failed, 1=Success)"
        ),
        height=600
    )
    
    return fig

def _create_combined_risk_analysis(df: pd.DataFrame) -> go.Figure:
    """Create combined risk score analysis visualization"""
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Combined Risk Distribution', 'Risk vs Success Analysis',
                       'High Risk Transactions', 'Risk Score Components'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # 1. Risk Distribution
    fig.add_trace(
        go.Histogram(x=df['combined_risk_score'], nbinsx=30, name='Risk Distribution'),
        row=1, col=1
    )
    
    # 2. Risk vs Success
    risk_bins = pd.cut(df['combined_risk_score'], bins=5)
    risk_success = df.groupby(risk_bins)['is_successful'].agg(['mean', 'count'])
    
    fig.add_trace(
        go.Scatter(
            x=risk_success.index.astype(str),
            y=risk_success['mean'],
            mode='lines+markers',
            name='Success Rate',
            line=dict(color='purple', width=2)
        ),
        row=1, col=2
    )
    
    # 3. High Risk Transactions
    high_risk_threshold = df['combined_risk_score'].quantile(0.95)
    high_risk = df[df['combined_risk_score'] > high_risk_threshold]
    
    if len(high_risk) > 0:
        fig.add_trace(
            go.Scatter(
                x=high_risk['combined_risk_score'],
                y=high_risk['amount'] if 'amount' in high_risk.columns else high_risk.index,
                mode='markers',
                name='High Risk',
                marker=dict(color='red', size=8, opacity=0.7)
            ),
            row=2, col=1
        )
    
    # 4. Risk Score Components
    risk_components = ['synthetic_score', 'geo_risk', 'speed_risk']
    available_components = [col for col in risk_components if col in df.columns]
    
    if available_components:
        component_means = df[available_components].mean()
        fig.add_trace(
            go.Bar(
                x=component_means.index,
                y=component_means.values,
                name='Average Component Risk'
            ),
            row=2, col=2
        )
    
    fig.update_layout(height=800, title_text="Combined Risk Score Analysis")
    fig.update_xaxes(title_text="Combined Risk Score", row=1, col=1)
    fig.update_yaxes(title_text="Frequency", row=1, col=1)
    fig.update_xaxes(title_text="Risk Bins", row=1, col=2)
    fig.update_yaxes(title_text="Success Rate", row=1, col=2)
    fig.update_xaxes(title_text="Risk Score", row=2, col=1)
    fig.update_yaxes(title_text="Amount", row=2, col=1)
    fig.update_xaxes(title_text="Risk Components", row=2, col=2)
    fig.update_yaxes(title_text="Average Risk Score", row=2, col=2)
    
    return fig

def _create_factor_correlations_heatmap(correlation_matrix: pd.DataFrame) -> go.Figure:
    """Create factor correlations heatmap"""
    
    fig = go.Figure(data=go.Heatmap(
        z=correlation_matrix.values,
        x=correlation_matrix.columns,
        y=correlation_matrix.columns,
        colorscale='RdBu',
        zmid=0,
        text=np.round(correlation_matrix.values, 3),
        texttemplate="%{text}",
        textfont={"size": 10}
    ))
    
    fig.update_layout(
        title="Factor Correlation Matrix",
        height=600,
        xaxis_title="Factors",
        yaxis_title="Factors"
    )
    
    return fig

def _create_suspicious_patterns_chart(df: pd.DataFrame) -> go.Figure:
    """Create suspicious patterns detection chart"""
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Suspicious User Agents', 'Suspicious Screen Resolutions',
                       'Unusual Transaction Times', 'Round Amount Detection'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # 1. Suspicious User Agents
    if 'browser_user_agent' in df.columns:
        suspicious_patterns = ['python', 'curl', 'wget', 'postman', 'selenium', 'headless']
        suspicious_counts = {}
        
        for pattern in suspicious_patterns:
            count = df['browser_user_agent'].str.lower().str.contains(pattern, na=False).sum()
            suspicious_counts[pattern] = count
        
        fig.add_trace(
            go.Bar(
                x=list(suspicious_counts.keys()),
                y=list(suspicious_counts.values()),
                name='Suspicious Patterns'
            ),
            row=1, col=1
        )
    
    # 2. Suspicious Screen Resolutions
    if all(col in df.columns for col in ['browser_screen_width', 'browser_screen_height']):
        suspicious_resolutions = ['0x0', '1x1', '100x100', '800x600', '1024x768']
        resolution_counts = {}
        
        for res in suspicious_resolutions:
            width, height = res.split('x')
            count = ((df['browser_screen_width'] == int(width)) & 
                    (df['browser_screen_height'] == int(height))).sum()
            resolution_counts[res] = count
        
        fig.add_trace(
            go.Bar(
                x=list(resolution_counts.keys()),
                y=list(resolution_counts.values()),
                name='Suspicious Resolutions'
            ),
            row=1, col=2
        )
    
    # 3. Unusual Transaction Times
    if 'created_at' in df.columns:
        df['hour'] = df['created_at'].dt.hour
        unusual_hours = (df['hour'] < 6) | (df['hour'] > 23)
        unusual_hour_counts = df[unusual_hours]['hour'].value_counts().sort_index()
        
        fig.add_trace(
            go.Bar(
                x=unusual_hour_counts.index,
                y=unusual_hour_counts.values,
                name='Unusual Hours'
            ),
            row=2, col=1
        )
    
    # 4. Round Amount Detection
    if 'amount' in df.columns:
        round_amounts = df['amount'].apply(lambda x: x % 100 == 0 if pd.notna(x) else False)
        round_amount_counts = round_amounts.value_counts()
        
        fig.add_trace(
            go.Pie(
                labels=['Non-Round', 'Round Amounts'],
                values=round_amount_counts.values,
                name='Amount Types'
            ),
            row=2, col=2
        )
    
    fig.update_layout(height=800, title_text="Suspicious Pattern Detection")
    fig.update_xaxes(title_text="Suspicious Patterns", row=1, col=1)
    fig.update_yaxes(title_text="Count", row=1, col=1)
    fig.update_xaxes(title_text="Screen Resolutions", row=1, col=2)
    fig.update_yaxes(title_text="Count", row=1, col=2)
    fig.update_xaxes(title_text="Hour of Day", row=2, col=1)
    fig.update_yaxes(title_text="Transaction Count", row=2, col=1)
    
    return fig
