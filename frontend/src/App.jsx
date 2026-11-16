import React from 'react';
import { RobotProvider, useRobot } from './core/RobotContext';
import { Header } from './components/Header';
import { WidgetCard } from './components/WidgetCard';
import { PLUGINS } from './plugins';

const Dashboard = () => {
  const { activePluginIds } = useRobot();

  const visiblePlugins = PLUGINS.filter((p) => activePluginIds.includes(p.id));

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header availablePlugins={PLUGINS} />

      <main
        style={{
          flex: 1,
          padding: '20px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '16px',
          alignContent: 'start',
          maxWidth: '1600px',
          margin: '0 auto',
          width: '100%'
        }}
      >
        {visiblePlugins.map((plugin) => {
          const Component = plugin.component;
          return (
            <WidgetCard
              key={plugin.id}
              title={plugin.name}
              icon={plugin.icon}
              colSpan={plugin.colSpan || 1}
            >
              <Component />
            </WidgetCard>
          );
        })}
      </main>
    </div>
  );
};

export default function App() {
  return (
    <RobotProvider>
      <Dashboard />
    </RobotProvider>
  );
}
