import React from 'react';
import { Toolbar } from 'primereact/toolbar';
import { Button } from 'primereact/button';
import { Tooltip } from 'primereact/tooltip';
import { Badge } from 'primereact/badge';

interface EditorToolbarProps {
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onSave: () => void;
  hasUnsavedChanges: boolean;
}

export const EditorToolbar: React.FC<EditorToolbarProps> = ({
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onSave,
  hasUnsavedChanges
}) => {
  const leftContent = (
    <div className="flex align-items-center gap-2">
      {/* History Controls */}
      <div className="history-controls">
        <Tooltip target=".undo-btn" content="Undo (Ctrl+Z)" position="bottom" />
        <Tooltip target=".redo-btn" content="Redo (Ctrl+Y)" position="bottom" />
        
        <Button
          icon="pi pi-undo"
          className="p-button-text p-button-sm undo-btn"
          onClick={onUndo}
          disabled={!canUndo}
          size="small"
        />
        <Button
          icon="pi pi-redo"
          className="p-button-text p-button-sm redo-btn"
          onClick={onRedo}
          disabled={!canRedo}
          size="small"
        />
      </div>
      
      <div className="p-toolbar-separator" />
      
      {/* Editor Actions */}
      <div className="editor-actions">
        <Tooltip target=".format-btn" content="Format Content" position="bottom" />
        <Button
          icon="pi pi-align-left"
          className="p-button-text p-button-sm format-btn"
          size="small"
        />
      </div>
    </div>
  );

  const rightContent = (
    <div className="flex align-items-center gap-2">
      {/* Save Status */}
      {hasUnsavedChanges && (
        <div className="unsaved-indicator">
          <Badge value="Unsaved Changes" severity="warning" />
        </div>
      )}
      
      {/* Quick Save */}
      <Tooltip target=".quick-save-btn" content="Save (Ctrl+S)" position="bottom" />
      <Button
        icon="pi pi-save"
        label="Save"
        className="p-button-sm quick-save-btn"
        onClick={onSave}
        severity={hasUnsavedChanges ? "success" : "secondary"}
        size="small"
      />
    </div>
  );

  return (
    <Toolbar 
      left={leftContent} 
      right={rightContent} 
      className="editor-toolbar"
      style={{ 
        padding: '0.5rem 1rem',
        borderRadius: '0',
        borderLeft: 'none',
        borderRight: 'none',
        borderTop: 'none'
      }}
    />
  );
};