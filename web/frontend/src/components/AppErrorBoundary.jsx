import { Component } from "react";

export class AppErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return <main className="app-error-page"><section className="app-error-card"><p className="eyebrow">Skill Passport</p><h1>We could not render this analysis.</h1><p>The analysis data may be incomplete. Your repository was not executed or installed.</p><div className="app-error-actions"><a className="btn-ghost" href="/">Return home</a><button className="btn-primary" onClick={() => window.location.reload()}>Try again</button></div></section></main>;
    }
    return this.props.children;
  }
}
